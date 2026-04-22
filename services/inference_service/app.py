from fastapi import FastAPI, HTTPException, status
import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor
from .schemas import InputData, Prediction, PredictResponse
from datetime import datetime
from .predictor import Predictor
from .load_model import fetch_model_with_retry, _MODEL_BYTES_CACHE
import os
import logging
from shared.utils.logging_utils import JSONFormatter
from asgi_correlation_id import CorrelationIdMiddleware, CorrelationIdFilter, correlation_id

reload_lock = asyncio.Lock()


logger = logging.getLogger(__name__)


def setup_logging():
    handler = logging.StreamHandler()
    formatter = JSONFormatter(os.getenv("SERVICE_NAME", "inference-service"))
    handler.setFormatter(formatter)
    # Add the filter to inject correlation_id into log records
    handler.addFilter(CorrelationIdFilter())
    logger.addHandler(handler)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
 
def _run_prediction(model_bytes: bytes, input_dict: dict):
    """
    Helper function that runs inside the ProcessPool worker.
    Instantiating the model here ensures it stays within the process memory.
    """
    predictor = Predictor(model_bytes)
    return predictor.predict(input_dict)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model_executor
    setup_logging()

    # Initialize Process Pool for CPU-bound scikit-learn work
    workers = 4
    model_executor = ProcessPoolExecutor(max_workers=workers)

    logger.info(
        "Application starting up", 
        extra={"event": "startup", "max_workers": workers}
    )

    yield

    logger.info("Application shutting down", extra={"event": "shutdown"})
    model_executor.shutdown(wait=True)
    logger.info("Executor shut down complete")


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CorrelationIdMiddleware,
    header_name="X-Correlation-ID",
    validator=None
)


@app.get("/health")
def health():
    logger.debug("Health check requested", extra={"event": "health_check"})
    return {"status": "ok"}


@app.post("/reload")
async def reload():
    global model_executor

    logger.info(
        "Model reload initiated", 
        extra={"event": "reload_started"}
    )
    async with reload_lock:
        try:
            # Clear the bytes cache in the main process
            _MODEL_BYTES_CACHE.clear()

            logger.info(
                "Model cache cleared", 
                extra={"event": "cache_cleared"}
            )

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
                }
            )

            return {"status": "success"}
        except Exception as e:
            logger.error(
                f"Failed to reload executor: {e}", 
                extra={"event": "reload_failed"},
                exc_info=True
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
            "event": "prediction_started"
        }
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
                    "error_type": "not_found"
                }
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
        except Exception as e:
            # Connection failure or MinIO timeout (Infrastructure Error)
            logger.error(
                f"Infrastructure error (MinIO) while fetching {model_name}",
                extra={
                    "request_id": request_id,
                    "model_name": model_name,
                    "event": "infrastructure_error",
                    "error_detail": str(e)
                },
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Model {model_name}:{model_version} is unavailable. {e}",
            )

        loop = asyncio.get_running_loop()
        logger.debug(
            "Transfer prediction to ProcessPool", 
            extra={"request_id": request_id, "model_name": model_name}
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
                "input_data": input_data.model_dump()
            },
            exc_info=True 
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
        extra={"event": "prediction_completed", **response.model_dump(mode="json")}
    )

    return response
