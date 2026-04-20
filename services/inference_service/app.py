from fastapi import FastAPI, HTTPException, status
import uuid
import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ProcessPoolExecutor
from schemas import InputData, Prediction, PredictResponse
from datetime import datetime
from predictor import Predictor
from load_model import fetch_model_with_retry, _MODEL_BYTES_CACHE
import os

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
    global model_executor

    # Initialize Process Pool for CPU-bound scikit-learn work
    model_executor = ProcessPoolExecutor(max_workers=4)

    yield

    model_executor.shutdown(wait=True)


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reload")
async def reload():
    global model_executor
    async with reload_lock:
        # Clear the bytes cache in the main process
        _MODEL_BYTES_CACHE.clear()

        # Spin up a fresh executor
        new_executor = ProcessPoolExecutor(max_workers=os.cpu_count())
        old_executor = model_executor
        model_executor = new_executor

        loop = asyncio.get_running_loop()
        # Background task to close old pool executor
        loop.run_in_executor(None, old_executor.shutdown, True)

        return {"status": "success"}


@app.post("/predict", response_model=PredictResponse)
async def predict(input_data: InputData, model_name: str, model_version: str):
    start_time = datetime.now()

    try:
        try:
            model_bytes = await fetch_model_with_retry(model_name, model_version)
        except ValueError as ve:
            # Model not found
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
        except Exception as e:
            # Connection failure or MinIO timeout (Infrastructure Error)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Model {model_name}:{model_version} is unavailable. {e}",
            )

        loop = asyncio.get_running_loop()
        label, score = await loop.run_in_executor(
            model_executor, _run_prediction, model_bytes, input_data.model_dump()
        )

        prediction = Prediction(label=label, score=score)
        status_msg = "success"
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        # Prediction logic crashed (Code Error)
        raise HTTPException(status_code=500, detail="Unexpected system error")

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

    return response
