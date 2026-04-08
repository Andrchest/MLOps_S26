import json

from fastapi import FastAPI
from datetime import datetime, timezone
import uuid
import asyncio
import asyncpg
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor
from schemas import *
from predictor import ChurnPredictor

model_path = "artifacts/model.joblib"
reload_lock = asyncio.Lock()


def init_worker(path):
    global predictor
    try:
        predictor = ChurnPredictor(path)
        print(f"Worker initialized successfully with model: {path}")
    except Exception as e:
        print(f"Failed to initialize worker with model {path}: {e}")


def predict_label(data):
    global predictor
    return predictor.predict(data)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model_executor, db_pool
    model_executor = ProcessPoolExecutor(max_workers=4, initializer=init_worker, initargs=(model_path,))

    db_pool = await asyncpg.create_pool(user="postgres", password="1234", database="MLOPS", host="localhost", port=5432)

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
        new_executor = ProcessPoolExecutor(
            max_workers=4,
            initializer=init_worker,
            initargs=(model_path,)
        )
        old_executor = model_executor
        model_executor = new_executor

        loop = asyncio.get_running_loop()
        # Background task to close old pool executor
        loop.run_in_executor(None, old_executor.shutdown, True)

        return {
            "status": "success",
            "message": "model reloaded and pool restarted"
        }


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
                response.status
            )
        print("SAVED: ", response.request_id)
    except Exception as e:
        print("FAILED: ", e)


@app.post("/predict", response_model=PredictResponse)
async def predict(input_data: InputData):
    start_time = datetime.now()

    try:
        loop = asyncio.get_running_loop()
        label, score = await loop.run_in_executor(
            model_executor,
            predict_label,
            input_data.model_dump()
        )

        prediction = Prediction(label=label, score=score)
        status = "success"
    except Exception as e:
        status = f"error: {str(e)}"
        prediction = Prediction(label=0, score=0.0)

    # latency
    latency = int((datetime.now() - start_time).total_seconds() * 1000)

    response = PredictResponse(
        request_id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        model_version="churn_model_v1",
        model_name="customer_churn_model",
        input_data=input_data,
        prediction=prediction,
        latency_ms=latency,
        status=status
    )


    asyncio.create_task(save_log(response))

    return response
