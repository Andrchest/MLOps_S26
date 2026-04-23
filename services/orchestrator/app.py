import logging
import os

import asyncpg
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from services.orchestrator.dataset_service import (
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
async def train(client_id: str, dataset_name: str, dataset_id: int):
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database is not available.")

    try:
        async with db_pool.acquire() as conn:
            existing = await conn.fetchval(
                "SELECT job_id FROM jobs WHERE client_id = $1",
                client_id,
            )

            if existing:
                return {"job_id": existing, "status": "pending"}

            job_id = await conn.fetchval(
                """
                INSERT INTO jobs (client_id, dataset_name, dataset_id, status)
                VALUES ($1, $2, $3, 'pending')
                RETURNING job_id
                """,
                client_id,
                dataset_name,
                dataset_id,
            )

        return {"job_id": job_id, "status": "pending"}

    except Exception:
        raise HTTPException(status_code=503, detail="Database error")


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


@app.post("/models/promote")
async def promote_model(
    model_name: str, model_version: str, deployed_by: str = "system"
):
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO deployments (model_name, model_version, deployed_by)
            VALUES ($1, $2, $3)
            """,
            model_name,
            model_version,
            deployed_by,
        )

    return {"status": "promoted"}


@app.get("/models/{model_name}/deployments")
async def get_model_deployments(model_name: str):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM deployments
            WHERE model_name = $1
            ORDER BY deployed_at DESC
            """,
            model_name,
        )

    return [dict(r) for r in rows]


@app.get("/models")
async def list_models():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT DISTINCT model_name FROM trained_models")
    return [r["model_name"] for r in rows]


@app.get("/deployments")
async def list_deployments():
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM deployments ORDER BY deployed_at DESC")
    return [dict(r) for r in rows]


@app.post("/models/rollback")
async def rollback(model_name: str):
    async with db_pool.acquire() as conn:
        last_two = await conn.fetch(
            """
            SELECT * FROM deployments
            WHERE model_name = $1
            ORDER BY deployed_at DESC
            LIMIT 2
        """,
            model_name,
        )

        if len(last_two) < 2:
            return {"error": "no previous version"}

        previous = last_two[1]

        await conn.execute(
            """
            UPDATE deployments
            SET status = 'active'
            WHERE deployment_id = $1
        """,
            previous["deployment_id"],
        )

    return {"status": "rolled back"}
