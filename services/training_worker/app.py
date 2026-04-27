import asyncpg
import asyncio
import logging
import os
import sys
from fastapi import FastAPI
from contextlib import asynccontextmanager

try:
    import db
    from worker import worker_loop
except ModuleNotFoundError:
    from . import db
    from .worker import worker_loop

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")


# Connection to Postgres
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("LIFESPAN: creating DB pool with retries")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "mlops")
    password = os.getenv("POSTGRES_PASSWORD", "mlops")
    database = os.getenv("POSTGRES_DB", "mlops")
    
    for attempt in range(30):
        try:
            db.db_pool = await asyncpg.create_pool(
                user=user, password=password, database=database,
                host=host, port=port,
            )
            logging.info("LIFESPAN: DB pool created on attempt %d, starting worker", attempt + 1)
            asyncio.create_task(worker_loop())
            logging.info("LIFESPAN: worker task started")
            yield
            logging.info("LIFESPAN: shutting down")
            await db.db_pool.close()
            return
        except Exception as exc:
            logging.warning("LIFESPAN: DB connection attempt %d failed: %s", attempt + 1, exc)
            await asyncio.sleep(2)
    logging.error("LIFESPAN: Failed to connect to database after 30 attempts")
    raise RuntimeError("Failed to connect to database")


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}
