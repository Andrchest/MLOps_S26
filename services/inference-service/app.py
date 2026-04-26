import asyncio
import json
import logging
import os
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import asyncpg
import pandas as pd
from fastapi import FastAPI, HTTPException, status
from load_model import _MODEL_BYTES_CACHE, fetch_model_bytes
from predictor import Predictor
from schemas import InputData, PredictResponse, Prediction

try:
    from drift_detection.service import analyze_drift, build_drift_visualization
except ModuleNotFoundError:
    from services.drift_detection.service import (
        analyze_drift,
        build_drift_visualization,
    )

reload_lock = asyncio.Lock()
logging.basicConfig(level=logging.INFO, format="%(message)s")

DRIFT_THRESHOLD = float(os.getenv("DRIFT_THRESHOLD", "2.0"))
LATEST_DRIFT_RESULTS: dict[str, dict[str, Any]] = {}


def _run_prediction(model_bytes: bytes, input_dict: dict):
    predictor = Predictor(model_bytes)
    return predictor.predict(input_dict)


def create_model_executor():
    try:
        return ProcessPoolExecutor(max_workers=4)
    except (OSError, PermissionError) as exc:
        logging.warning(
            "Falling back to ThreadPoolExecutor because ProcessPoolExecutor "
            "is unavailable: %s",
            exc,
        )
        return ThreadPoolExecutor(max_workers=4)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model_executor, db_pool

    db_pool = await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER", "mlops"),
        password=os.getenv("POSTGRES_PASSWORD", "mlops"),
        database=os.getenv("POSTGRES_DB", "mlops"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )
    model_executor = create_model_executor()

    yield

    model_executor.shutdown(wait=True)
    await db_pool.close()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/reload")
async def reload():
    global model_executor
    async with reload_lock:
        _MODEL_BYTES_CACHE.clear()

        new_executor = create_model_executor()
        old_executor = model_executor
        model_executor = new_executor

        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, old_executor.shutdown, True)

        return {"status": "success"}


async def save_log(response: PredictResponse):
    try:
        query = """
        INSERT INTO prediction_logs (
            request_id,
            timestamp,
            model_version,
            model_name,
            input_data,
            prediction,
            latency_ms,
            status
        )
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
        """

        async with db_pool.acquire() as conn:
            await conn.execute(
                query,
                response.request_id,
                response.timestamp,
                response.model_version,
                response.model_name,
                json.dumps(response.input_data.model_dump()),
                json.dumps(response.prediction.model_dump()),
                response.latency_ms,
                response.status,
            )
    except Exception as exc:
        logging.warning("Failed to save prediction log: %s", exc)


async def get_model_context(model_name: str, model_version: str) -> dict[str, Any] | None:
    query = """
    SELECT
        tm.parameters,
        j.dataset_id,
        j.dataset_name
    FROM trained_models tm
    JOIN jobs j ON j.job_id = tm.job_id
    WHERE tm.model_name = $1 AND tm.model_version = $2
    ORDER BY tm.created_at DESC NULLS LAST, tm.job_id DESC
    LIMIT 1
    """
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(query, model_name, model_version)
    except Exception as exc:
        logging.warning("Failed to fetch model context: %s", exc)
        return None

    if row is None:
        return None

    parameters = row["parameters"]
    if isinstance(parameters, str):
        parameters = json.loads(parameters)

    return {
        "dataset_id": row["dataset_id"],
        "dataset_name": row["dataset_name"],
        "parameters": parameters or {},
    }


async def create_retraining_job(dataset_name: str, dataset_id: int) -> int | None:
    query_active = """
    SELECT job_id
    FROM jobs
    WHERE dataset_name = $1
      AND dataset_id = $2
      AND status IN ('pending', 'running', 'persisting')
    ORDER BY job_id DESC
    LIMIT 1
    """
    query_insert = """
    INSERT INTO jobs (dataset_name, dataset_id, status)
    VALUES ($1, $2, 'pending')
    RETURNING job_id
    """
    async with db_pool.acquire() as conn:
        active_job = await conn.fetchval(query_active, dataset_name, dataset_id)
        if active_job:
            return None
        return await conn.fetchval(query_insert, dataset_name, dataset_id)


async def evaluate_drift(
    request_id: str,
    model_name: str,
    model_version: str,
    input_data: InputData,
) -> dict[str, Any] | None:
    model_context = await get_model_context(model_name, model_version)
    if not model_context:
        return None

    reference_profile = model_context["parameters"].get("reference_profile")
    if not reference_profile:
        return None

    drift_result = analyze_drift(
        reference_profile,
        pd.DataFrame([input_data.model_dump()]),
        threshold=DRIFT_THRESHOLD,
    )

    retraining_job_id = None
    if drift_result["drift_detected"]:
        retraining_job_id = await create_retraining_job(
            model_context["dataset_name"],
            model_context["dataset_id"],
        )
        logging.warning(
            "Drift detected for %s:%s score=%.4f retraining_job_id=%s",
            model_name,
            model_version,
            drift_result["drift_score"],
            retraining_job_id,
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
    return result


@app.post("/predict", response_model=PredictResponse)
async def predict(input_data: InputData, model_name: str, model_version: str):
    start_time = datetime.now()

    try:
        model_bytes = await fetch_model_bytes(model_name, model_version)
        loop = asyncio.get_running_loop()
        label, score = await loop.run_in_executor(
            model_executor, _run_prediction, model_bytes, input_data.model_dump()
        )
        prediction = Prediction(label=label, score=score)
        status_msg = "success"
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        status_msg = f"error: {exc}"
        prediction = Prediction(label=0, score=0.0)

    latency = int((datetime.now() - start_time).total_seconds() * 1000)
    response = PredictResponse(
        request_id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        model_version=model_version,
        model_name=model_name,
        input_data=input_data,
        prediction=prediction,
        latency_ms=latency,
        status=status_msg,
    )
    asyncio.create_task(save_log(response))
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
