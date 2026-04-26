from fastapi import FastAPI, HTTPException
import asyncpg
import os
import asyncio
import logging
from shared.utils.logging_utils import setup_logging
from asgi_correlation_id import CorrelationIdMiddleware

app = FastAPI()
app.add_middleware(
    CorrelationIdMiddleware, header_name="X-Correlation-ID", validator=None
)

# Initialize logger
logger = logging.getLogger(__name__)

from services.orchestrator.dataset_service import (
    DatasetRecord,
    dataset_registry,
    register_uploaded_dataset,
    storage_client,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI()
db_pool = None


async def create_db_pool_with_retry(max_retries=10, retry_delay=2):
    """Create DB pool with retry logic for resilience."""
    global db_pool
    for attempt in range(max_retries):
        try:
            logger.info(f"Creating DB pool (attempt {attempt + 1}/{max_retries})")
            db_pool = await asyncpg.create_pool(
                user=os.getenv("POSTGRES_USER", "mlops"),
                password=os.getenv("POSTGRES_PASSWORD", "mlops"),
                database=os.getenv("POSTGRES_DB", "mlops"),
                host=os.getenv("POSTGRES_HOST", "postgres"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
            )
            logger.info("DB pool created successfully", extra={"event": "db_pool_ready"})
            return db_pool
        except Exception as e:
            logger.warning(f"DB connection failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                raise Exception(f"Could not connect to DB after {max_retries} attempts")


@app.on_event("startup")
async def startup():
    setup_logging("orchestrator")
    logger.info("Orchestrator starting up...", extra={"event": "startup_initiated"})
    await create_db_pool_with_retry()
    logger.info("Orchestrator startup complete.", extra={"event": "startup_finished"})


@app.on_event("shutdown")
async def shutdown():
    logger.info("Orchestrator shutting down...", extra={"event": "shutdown_initiated"})
    if db_pool:
        await db_pool.close()
    logger.info("Orchestrator shutdown complete.", extra={"event": "shutdown_finished"})


@app.get("/health")
def health():
    logger.debug("Health check requested", extra={"event": "health_check"})
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
    logger.info(
        f"Checking status for job {job_id}",
        extra={"job_id": job_id, "event": "status_check_requested"},
    )
    async with db_pool.acquire() as conn:
        status = await conn.fetchval(
            """
            SELECT (status)
            from jobs
            WHERE job_id = $1
            """,
            job_id,
        )
        if status is None:
            logger.warning(
                f"Job {job_id} not found",
                extra={"job_id": job_id, "event": "job_not_found"},
            )
            raise HTTPException(status_code=404, detail="Job not found")

        logger.info(
            "Dataset registration started", extra={"event": "dataset_reg_started"}
        )
        return {"job_id": job_id, "status": status}


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
