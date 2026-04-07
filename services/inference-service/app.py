from fastapi import FastAPI
from datetime import datetime, timezone
import uuid
import asyncio
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
    global model_executor
    model_executor = ProcessPoolExecutor(max_workers=4, initializer=init_worker, initargs=(model_path,))
    yield
    model_executor.shutdown(wait=True)


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
        timestamp=datetime.now(timezone.utc).isoformat() + "Z",
        model_version="churn_model_v1",
        model_name="customer_churn_model",
        input_data=input_data,
        prediction=prediction,
        latency_ms=latency,
        status=status
    )

    return response
