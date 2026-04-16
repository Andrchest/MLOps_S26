import json
from fastapi import FastAPI, HTTPException, status
import uuid
import asyncio
import asyncpg
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor
from schemas import InputData, Prediction, PredictResponse
from datetime import datetime
from predictor import Predictor
import os
from load_model import fetch_model_bytes, _MODEL_BYTES_CACHE

reload_lock = asyncio.Lock()


def _run_prediction(model_bytes: bytes, input_dict: dict):
    """
    Helper function that runs inside the ProcessPool worker.
    Instantiating the model here ensures it stays within the process memory.
    """
    predictor = Predictor(model_bytes)
    return predictor.predict(input_dict)


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

    # Initialize Process Pool for CPU-bound scikit-learn work
    model_executor = ProcessPoolExecutor(max_workers=4)

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
        # Clear the bytes cache in the main process
        _MODEL_BYTES_CACHE.clear()

        new_executor = ProcessPoolExecutor(max_workers=4)
        old_executor = model_executor
        model_executor = new_executor

        loop = asyncio.get_running_loop()
        # Background task to close old pool executor
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
        print("SAVED: ", response.request_id)
    except Exception as e:
        print("FAILED: ", e)


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
    except ValueError as ve:
        # Model not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        # Code exception
        status_msg = f"error: {str(e)}"
        prediction = Prediction(label=0, score=0.0)

    # latency
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

    return response
