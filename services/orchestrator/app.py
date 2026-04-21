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


@app.post("/train", status_code=201)
async def train(dataset_name: str, dataset_id: int):
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database is not available.")

    async with db_pool.acquire() as conn:
        # Idempotency: check if exact same request was already processed
        existing = await conn.fetchval(
            """
            SELECT job_id FROM jobs
            WHERE dataset_name = $1 AND dataset_id = $2 AND status = 'pending'
            LIMIT 1
            """,
            dataset_name,
            dataset_id,
        )
        if existing:
            return {"job_id": existing, "status": "pending"}

        job_id = await conn.fetchval(
            """
            INSERT INTO jobs (dataset_id, status)
            VALUES ($1, 'pending')
            RETURNING job_id
            """,
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
            SELECT (status)
            from jobs
            WHERE job_id = $1
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


@app.get("/models/{model_name}/deployments")
async def get_deployment_name(model_name: str):
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database is not available.")

    async with db_pool.acquire() as conn:
        models = await conn.fetch(
            """
            SELECT * FROM deployments
            WHERE model_name = $1
            ORDER BY deployment_id DESC
            """,
            model_name,
        )
    if not models:
        raise HTTPException(status_code=404, detail="Model not found.")
    return [dict(m) for m in models]


@app.get("/deployments/{deployment_id}")
async def get_deployment_id(deployment_id: int):
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database is not available.")
    async with db_pool.acquire() as conn:
        deployment = await conn.fetchrow(
            """
            SELECT * 
            from deployments
            WHERE deployment_id = $1
            """,
            deployment_id,
        )
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment is not available.")
    return dict(deployment)


@app.post("/deployments/{deployment_id}/rollback")
async def deployment_rollback(deployment_id: int):
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database is not available.")
    async with db_pool.acquire() as conn:
        current_vers = await conn.fetchrow(
            """
            SELECT model_name, model_version
            from deployments
            WHERE deployment_id = $1
            """,
            deployment_id,
        )

        if not current_vers:
            raise HTTPException(status_code=404, detail="Deployment not found.")

        model_name = current_vers["model_name"]
        previous_vers = await conn.fetchrow(
            """
            SELECT deployment_id, model_name, model_version
            FROM deployments
            WHERE model_name = $1 AND deployment_id < $2
            ORDER BY deployment_id DESC
            LIMIT 1
        """,
            model_name,
            deployment_id,
        )
        if not previous_vers:
            raise HTTPException(
                status_code=404, detail="Previous deployment is not available."
            )

        previous = previous_vers["model_version"]

        rolled_vers_id = await conn.fetchval(
            """
            INSERT INTO deployments (model_name, model_version, status)
            VALUES ($1, $2, 'rolled_back')
            RETURNING deployment_id
            """,
            model_name,
            previous,
        )
        return {
            "status": "rolled back successfully",
            "deployment_id": rolled_vers_id,
            "model_name": model_name,
            "model_version": previous,
        }
