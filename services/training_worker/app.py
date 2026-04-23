import asyncpg
import asyncio
import logging
import os
from services.training_worker import db
from services.training_worker.worker import worker_loop
from fastapi import FastAPI
from contextlib import asynccontextmanager
from shared.utils.logging_utils import setup_logging
from asgi_correlation_id import CorrelationIdMiddleware

logger = logging.getLogger(__name__)


# Connection to Postgres
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging("training-worker")
    logger.info("Creating DB pool", extra={"event": "db_pool_creating"})
    db.db_pool = await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER", "mlops"),
        password=os.getenv("POSTGRES_PASSWORD", "mlops"),
        database=os.getenv("POSTGRES_DB", "mlops"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )
    logger.info("DB pool created successfully", extra={"event": "db_pool_ready"})
    logger.info("Starting background worker task", extra={"event": "worker_task_start"})
    asyncio.create_task(worker_loop())
    yield
    logger.info("Shutting down application", extra={"event": "shutdown_initiated"})
    await db.db_pool.close()
    logger.info("DB pool closed", extra={"event": "db_pool_closed"})


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CorrelationIdMiddleware, header_name="X-Correlation-ID", validator=None
)


@app.get("/health")
async def health():
    logger.debug("Health check requested", extra={"event": "health_check"})
    return {"status": "ok"}
