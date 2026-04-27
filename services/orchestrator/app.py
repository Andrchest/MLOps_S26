import logging
import os

import asyncpg
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

try:
    from dataset_service import (
        DatasetRecord,
        dataset_registry,
        register_uploaded_dataset,
        storage_client,
    )
except ModuleNotFoundError:
    from .dataset_service import (
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
async def train(dataset_name: str, dataset_id: int, dataset_path: str = None):
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database is not available.")

    async with db_pool.acquire() as conn:
        job_id = await conn.fetchval(
            """
            INSERT INTO jobs (dataset_name, dataset_id, dataset_path, status)
            VALUES ($1, $2, $3, 'pending')
            RETURNING job_id
            """,
            dataset_name,
            dataset_id,
            dataset_path,
        )

    return {"job_id": job_id, "status": "pending"}


@app.get("/jobs")
async def list_jobs():
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database is not available.")

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT job_id, dataset_name, dataset_id, dataset_path, status, created_at
            FROM jobs
            ORDER BY job_id DESC
            """
        )

    jobs = []
    for row in rows:
        jobs.append({
            "job_id": row["job_id"],
            "dataset_name": row["dataset_name"],
            "dataset_id": row["dataset_id"],
            "dataset_path": row["dataset_path"],
            "status": row["status"],
            "created_at": str(row["created_at"]),
        })

    return {"jobs": jobs}


@app.get("/jobs/{job_id}")
async def get_status(job_id: int):
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database is not available.")

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT job_id, dataset_name, dataset_id, dataset_path, status, created_at
            FROM jobs WHERE job_id = $1
            """,
            job_id,
        )

    if row is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    return {
        "job_id": row["job_id"],
        "dataset_name": row["dataset_name"],
        "dataset_id": row["dataset_id"],
        "dataset_path": row["dataset_path"],
        "status": row["status"],
        "created_at": str(row["created_at"]),
    }


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


@app.get("/models")
async def list_models():
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database is not available.")

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT tm.model_name, tm.model_version, tm.model_path,
                   tm.metrics, tm.parameters, tm.created_at,
                   j.dataset_name, j.dataset_id
            FROM trained_models tm
            JOIN jobs j ON j.job_id = tm.job_id
            ORDER BY tm.created_at DESC
            """
        )

    models = []
    for row in rows:
        models.append({
            "model_name": row["model_name"],
            "model_version": row["model_version"],
            "model_path": row["model_path"],
            "metrics": row["metrics"],
            "parameters": row["parameters"],
            "created_at": str(row["created_at"]),
            "dataset_name": row["dataset_name"],
            "dataset_id": row["dataset_id"],
        })

    return {"models": models}


@app.get("/deployments")
async def list_deployments():
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database is not available.")

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT deployment_id, model_name, model_version, status,
                   deployed_at, deployed_by
            FROM deployments
            ORDER BY deployed_at DESC
            """
        )

    deployments = []
    for row in rows:
        deployments.append({
            "deployment_id": row["deployment_id"],
            "model_name": row["model_name"],
            "model_version": row["model_version"],
            "status": row["status"],
            "deployed_at": str(row["deployed_at"]),
            "deployed_by": row["deployed_by"],
        })

    return {"deployments": deployments}


@app.post("/promote")
async def promote_model(
    model_name: str = Form(...),
    model_version: str = Form(...),
    deployed_by: str = Form(default="api"),
):
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database is not available.")

    async with db_pool.acquire() as conn:
        # Verify the model exists in trained_models
        model = await conn.fetchrow(
            """
            SELECT job_id, model_name, model_version, model_path
            FROM trained_models
            WHERE model_name = $1 AND model_version = $2
            """,
            model_name,
            model_version,
        )

        if model is None:
            raise HTTPException(
                status_code=404,
                detail=f"Model {model_name}:{model_version} not found.",
            )

        # Check if already deployed
        existing = await conn.fetchrow(
            """
            SELECT deployment_id FROM deployments
            WHERE model_name = $1 AND model_version = $2 AND status = 'active'
            """,
            model_name,
            model_version,
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Model {model_name}:{model_version} is already deployed.",
            )

        # Create deployment record
        deployment_id = await conn.fetchval(
            """
            INSERT INTO deployments (model_name, model_version, status, deployed_by)
            VALUES ($1, $2, 'active', $3)
            RETURNING deployment_id
            """,
            model_name,
            model_version,
            deployed_by,
        )

    return {
        "deployment_id": deployment_id,
        "model_name": model_name,
        "model_version": model_version,
        "status": "active",
        "model_path": model["model_path"],
    }
