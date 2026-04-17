import logging
import os

import asyncpg
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from dataset_service import (
    DatasetRecord,
    dataset_registry,
    register_uploaded_dataset,
    storage_client,
)


logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI()
db_pool = None


async def init_db() -> None:
    global db_pool
    db_pool = await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER", "mlops"),
        password=os.getenv("POSTGRES_PASSWORD", "mlops"),
        database=os.getenv("POSTGRES_DB", "mlops"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )


@app.on_event("startup")
async def startup() -> None:
    try:
        await init_db()
    except Exception as exc:
        logging.warning("Failed to initialize database pool: %s", exc)


@app.on_event("shutdown")
async def shutdown() -> None:
    if db_pool is not None:
        await db_pool.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/train")
async def train(dataset_name: str, dataset_id: int):
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database is not available.")

    async with db_pool.acquire() as conn:
        job_id = await conn.fetchval(
            """
            INSERT INTO jobs (dataset_name, dataset_id, status)
            VALUES ($1, $2, 'pending')
            RETURNING job_id
            """,
            dataset_name,
            dataset_id,
        )

    return {"job_id": job_id, "status": "pending"}


@app.get("/jobs/{job_id}")
async def get_status(job_id: int):
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database is not available.")

    async with db_pool.acquire() as conn:
        status = await conn.fetchval(
            """
            SELECT status FROM jobs WHERE job_id = $1
            """,
            job_id,
        )

    return {"job_id": job_id, "status": status}


@app.post("/datasets", response_model=DatasetRecord)
async def upload_and_register_dataset(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Dataset file name is required.")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV datasets are supported.")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded dataset is empty.")

    try:
        return register_uploaded_dataset(
            filename=file.filename,
            payload=payload,
            content_type=file.content_type or "text/csv",
            name=name,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to upload dataset to object storage: {exc}",
        ) from exc


@app.get("/datasets/{dataset_id}", response_model=DatasetRecord)
def get_dataset(dataset_id: int):
    dataset = dataset_registry.get(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset
