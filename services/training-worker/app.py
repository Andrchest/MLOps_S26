import time
import joblib
import io
from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncpg
from minio_client import load_dataset
import asyncio
from sklearn.dummy import DummyClassifier


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    db_pool = await asyncpg.create_pool(
        user="postgres", password="1234", database="MLOPS", host="localhost", port=5432
    )
    yield
    await db_pool.close()


app = FastAPI(lifespan=lifespan)

# while True:
#     print("worker polling...")
#     time.sleep(5)

global db_pool


async def get_job(job_id: int):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT job_id, dataset_name, dataset_id
            FROM jobs
            WHERE job_id=$1 AND status='pending'
            """,
            job_id
        )
        return row


async def save_trained_model(job_id: int, model, model_name: str, model_version: str):
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    model_bytes = buffer.getvalue()

    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO trained_models (job_id, model_name, model_version, model)
            VALUES ($1, $2, $3, $4)
            """,
            job_id,
            model_name,
            model_version,
            model_bytes,
        )

