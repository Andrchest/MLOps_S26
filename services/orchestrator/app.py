from fastapi import FastAPI, HTTPException
import asyncpg
import os
import logging
from shared.utils.logging_utils import setup_logging
from asgi_correlation_id import CorrelationIdMiddleware

app = FastAPI()
app.add_middleware(
    CorrelationIdMiddleware, header_name="X-Correlation-ID", validator=None
)

# Initialize logger
logger = logging.getLogger(__name__)


db_pool = None


async def init_db():
    global db_pool
    logger.info("Creating DB pool", extra={"event": "db_pool_creating"})
    db_pool = await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER", "mlops"),
        password=os.getenv("POSTGRES_PASSWORD", "mlops"),
        database=os.getenv("POSTGRES_DB", "mlops"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )
    logger.info("DB pool created successfully", extra={"event": "db_pool_ready"})


@app.on_event("startup")
async def startup():
    setup_logging("orchestrator")
    logger.info("Orchestrator starting up...", extra={"event": "startup_initiated"})
    await init_db()
    logger.info("Orchestrator startup complete.", extra={"event": "startup_finished"})


@app.on_event("shutdown")
async def shutdown():
    logger.info("Orchestrator shutting down...", extra={"event": "shutdown_initiated"})
    await db_pool.close()
    logger.info("Orchestrator shutdown complete.", extra={"event": "shutdown_finished"})


@app.get("/health")
def health():
    logger.debug("Health check requested", extra={"event": "health_check"})
    return {"status": "ok"}


@app.post("/train")
async def train(dataset_name: str, dataset_id: int):
    log_ctx = {"dataset_name": dataset_name, "dataset_id": dataset_id}
    logger.info(
        "Training job creation requested",
        extra={**log_ctx, "event": "train_request_received"},
    )
    try:
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
            logger.info(
                "Training job created",
                extra={**log_ctx, "job_id": job_id, "event": "job_created_in_db"},
            )
            return {"job_id": job_id, "status": "pending"}
    except Exception as e:
        logger.error(
            f"Failed to create job: {e}",
            extra={**log_ctx, "event": "job_creation_failed"},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to create training job")


@app.get("/jobs/{job_id}")
async def get_status(job_id: int):
    logger.info(
        f"Checking status for job {job_id}",
        extra={"job_id": job_id, "event": "status_check_requested"},
    )
    async with db_pool.acquire() as conn:
        status = await conn.fetchval(
            """
            SELECT status FROM jobs WHERE job_id = $1
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


@app.post("/datasets")
def register_dataset():
    logger.info("Dataset registration started", extra={"event": "dataset_reg_started"})
    return {"status": "ok"}
