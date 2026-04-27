from fastapi import FastAPI, HTTPException, status
import asyncio
import json
import os
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
import asyncpg

from services.inference_service.schemas import InputData, Prediction, PredictResponse
from services.inference_service.predictor import Predictor
from services.inference_service.load_model import (
    fetch_model_with_retry,
    _MODEL_BYTES_CACHE,
    get_minio_circuit_state,
)
from services.inference_service.circuit_breaker import registry
import logging
from shared.utils.logging_utils import setup_logging
from asgi_correlation_id import CorrelationIdMiddleware, correlation_id

try:
    from drift_detection.service import analyze_drift, build_drift_visualization
except ModuleNotFoundError:
    from services.drift_detection.service import analyze_drift, build_drift_visualization

reload_lock = asyncio.Lock()

DB_POOL = None
DRIFT_THRESHOLD = float(os.getenv("DRIFT_THRESHOLD", "2.0"))
LATEST_DRIFT_RESULTS: dict[str, dict] = {}


logger = logging.getLogger(__name__)


def _run_prediction(model_bytes: bytes, input_dict: dict):
    """
    Helper function that runs inside the ProcessPool worker.
    Instantiating the model here ensures it stays within the process memory.
    """
    predictor = Predictor(model_bytes)
    return predictor.predict(input_dict)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model_executor, DB_POOL
    setup_logging("inference-service")

    # Initialize DB pool for model context and retraining (with retries)
    db_host = os.getenv("POSTGRES_HOST", "postgres")
    db_port = int(os.getenv("POSTGRES_PORT", "5432"))
    db_user = os.getenv("POSTGRES_USER", "mlops")
    db_password = os.getenv("POSTGRES_PASSWORD", "mlops")
    db_name = os.getenv("POSTGRES_DB", "mlops")

    for attempt in range(30):
        try:
            DB_POOL = await asyncpg.create_pool(
                user=db_user, password=db_password, database=db_name,
                host=db_host, port=db_port,
            )
            logger.info("DB pool created on attempt %d", attempt + 1)
            break
        except Exception as exc:
            logger.warning("DB connection attempt %d failed: %s", attempt + 1, exc)
            await asyncio.sleep(2)
    else:
        raise RuntimeError("Failed to connect to database after 30 attempts")

    # Initialize Process Pool for CPU-bound scikit-learn work
    workers = 4
    model_executor = ProcessPoolExecutor(max_workers=workers)

    logger.info(
        "Application starting up", extra={"event": "startup", "max_workers": workers}
    )

    yield

    logger.info("Application shutting down", extra={"event": "shutdown"})
    model_executor.shutdown(wait=True)
    await DB_POOL.close()
    logger.info("Executor shut down complete")


async def get_model_context(model_name: str, model_version: str) -> dict | None:
    if DB_POOL is None:
        return None
    query = """
    SELECT tm.parameters, j.dataset_id, j.dataset_name, j.dataset_path
    FROM trained_models tm
    JOIN jobs j ON j.job_id = tm.job_id
    WHERE tm.model_name = $1 AND tm.model_version = $2
    ORDER BY tm.created_at DESC NULLS LAST, tm.job_id DESC
    LIMIT 1
    """
    try:
        async with DB_POOL.acquire() as conn:
            row = await conn.fetchrow(query, model_name, model_version)
    except Exception as exc:
        logger.warning("Failed to fetch model context: %s", exc)
        return None

    if row is None:
        return None

    parameters = row["parameters"]
    if isinstance(parameters, str):
        parameters = json.loads(parameters)

    return {
        "dataset_id": row["dataset_id"],
        "dataset_name": row["dataset_name"],
        "dataset_path": row["dataset_path"],
        "parameters": parameters or {},
    }


async def create_retraining_job(dataset_name: str, dataset_id: int, dataset_path: str = None) -> int | None:
    query_active = """
    SELECT job_id FROM jobs
    WHERE dataset_name = $1 AND dataset_id = $2
    AND status IN ('pending', 'running', 'persisting')
    ORDER BY job_id DESC LIMIT 1
    """
    query_insert = """
    INSERT INTO jobs (dataset_name, dataset_id, dataset_path, status)
    VALUES ($1, $2, $3, 'pending')
    RETURNING job_id
    """
    try:
        async with DB_POOL.acquire() as conn:
            active_job = await conn.fetchval(query_active, dataset_name, dataset_id)
            if active_job:
                return None
            return await conn.fetchval(query_insert, dataset_name, dataset_id, dataset_path)
    except Exception as exc:
        logger.warning("Failed to create retraining job: %s", exc)
        return None


async def evaluate_drift(request_id: str, model_name: str, model_version: str, input_data: InputData) -> None:
    model_context = await get_model_context(model_name, model_version)
    if not model_context:
        return

    reference_profile = model_context["parameters"].get("reference_profile")
    if not reference_profile:
        return

    drift_result = analyze_drift(
        reference_profile,
        [input_data.model_dump()],
        threshold=DRIFT_THRESHOLD,
    )

    retraining_job_id = None
    if drift_result["drift_detected"]:
        retraining_job_id = await create_retraining_job(
            model_context["dataset_name"],
            model_context["dataset_id"],
            model_context.get("dataset_path"),
        )
        logger.warning(
            "Drift detected for %s:%s score=%.4f retraining_job_id=%s",
            model_name, model_version, drift_result["drift_score"], retraining_job_id,
        )

    result = build_drift_visualization(drift_result)
    result["request_id"] = request_id
    result["model_name"] = model_name
    result["model_version"] = model_version
    result["dataset_name"] = model_context["dataset_name"]
    result["retraining_job_id"] = retraining_job_id
    result["timestamp"] = datetime.now().isoformat()

    cache_key = f"{model_name}:{model_version}"
    LATEST_DRIFT_RESULTS[cache_key] = result


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CorrelationIdMiddleware, header_name="X-Correlation-ID", validator=None
)


@app.get("/health")
async def health():
    logger.debug("Health check requested", extra={"event": "health_check"})

    minio_state = await get_minio_circuit_state()
    db_available = True
    try:
        async with DB_POOL.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception:
        db_available = False

    return {
        "status": "ok" if minio_state["available"] and db_available else "degraded",
        "minio_circuit": minio_state,
        "db": "connected" if db_available else "unavailable",
    }


@app.post("/reload")
async def reload():
    global model_executor

    logger.info("Model reload initiated", extra={"event": "reload_started"})
    async with reload_lock:
        try:
            # Clear the bytes cache in the main process
            _MODEL_BYTES_CACHE.clear()

            logger.info("Model cache cleared", extra={"event": "cache_cleared"})

            # Spin up a fresh executor
            new_executor = ProcessPoolExecutor(max_workers=os.cpu_count())
            old_executor = model_executor
            model_executor = new_executor

            loop = asyncio.get_running_loop()

            # Background task to close old pool executor
            def safe_shutdown(executor):
                try:
                    executor.shutdown(wait=True)
                    logger.info("Old executor finished tasks and shut down.")
                except Exception as e:
                    logger.error(f"Error during old executor shutdown: {e}")

            loop = asyncio.get_running_loop()
            # Запускаем фоновую задачу "выключения"
            loop.run_in_executor(None, safe_shutdown, old_executor)

            logger.info(
                "Executor reloaded successfully",
                extra={
                    "event": "reload_success",
                },
            )

            return {"status": "success"}
        except Exception as e:
            logger.error(
                f"Failed to reload executor: {e}",
                extra={"event": "reload_failed"},
                exc_info=True,
            )
            raise HTTPException(status_code=500, detail="Reload failed")


@app.post("/predict", response_model=PredictResponse)
async def predict(input_data: InputData, model_name: str, model_version: str):
    request_id = correlation_id.get()
    logger.info(
        f"Starting prediction for {model_name}:{model_version}",
        extra={
            "model_name": model_name,
            "model_version": model_version,
            "request_id": request_id,
            "input_data": input_data.model_dump(),
            "event": "prediction_started",
        },
    )

    start_time = datetime.now()

    try:
        try:
            model_bytes = await fetch_model_with_retry(model_name, model_version)
        except ValueError as ve:
            # Model not found
            logger.warning(
                f"Model not found: {model_name}:{model_version}",
                extra={
                    "request_id": request_id,
                    "model_name": model_name,
                    "model_version": model_version,
                    "event": "model_fetch_failed",
                    "error_type": "not_found",
                },
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
        except Exception as e:
            # Connection failure, MinIO timeout, or circuit breaker open
            from services.inference_service.circuit_breaker import CircuitBreakerError

            if isinstance(e, CircuitBreakerError):
                logger.warning(
                    "Circuit breaker open for %s - returning 503",
                    e.service,
                    extra={
                        "request_id": request_id,
                        "model_name": model_name,
                        "event": "circuit_breaker_open",
                        "circuit_state": e.state.value,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Model service temporarily unavailable (circuit breaker: {e.state.value}).",
                )
            logger.error(
                f"Infrastructure error (MinIO) while fetching {model_name}",
                extra={
                    "request_id": request_id,
                    "model_name": model_name,
                    "event": "infrastructure_error",
                    "error_detail": str(e),
                },
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Model {model_name}:{model_version} is unavailable. {e}",
            )

        loop = asyncio.get_running_loop()
        logger.debug(
            "Transfer prediction to ProcessPool",
            extra={"request_id": request_id, "model_name": model_name},
        )
        label, score = await loop.run_in_executor(
            model_executor, _run_prediction, model_bytes, input_data.model_dump()
        )

        prediction = Prediction(label=label, score=score)
        status_msg = "success"
    except HTTPException:
        raise
    except Exception as e:
        logger.critical(
            f"Prediction logic crashed: {type(e).__name__}: {e}",
            extra={
                "request_id": request_id,
                "model_name": model_name,
                "model_version": model_version,
                "event": "prediction_runtime_error",
                "input_data": input_data.model_dump(),
            },
            exc_info=True,
        )
        # Prediction logic crashed (Code Error)
        raise HTTPException(status_code=500, detail="Unexpected system error")

    # latency
    latency = int((datetime.now() - start_time).total_seconds() * 1000)

    response = PredictResponse(
        request_id=request_id,
        timestamp=datetime.now(),
        model_version=model_version,
        model_name=model_name,
        input_data=input_data,
        prediction=prediction,
        latency_ms=latency,
        status=status_msg,
    )

    logger.info(
        "Prediction successful",
        extra={"event": "prediction_completed", **response.model_dump(mode="json")},
    )

    # Evaluate drift in background (non-blocking)
    asyncio.create_task(
        evaluate_drift(
            request_id=response.request_id,
            model_name=model_name,
            model_version=model_version,
            input_data=input_data,
        )
    )

    return response


@app.get("/drift/visualization")
async def get_drift_visualization(model_name: str, model_version: str):
    cache_key = f"{model_name}:{model_version}"
    payload = LATEST_DRIFT_RESULTS.get(cache_key)
    if payload is None:
        raise HTTPException(status_code=404, detail="Drift result not found.")
    return payload
