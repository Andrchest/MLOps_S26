import asyncpg
import asyncio
import logging
import os
import sys
import services.training_worker.db as db
from fastapi import FastAPI
from contextlib import asynccontextmanager
from services.training_worker.worker import worker_loop

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")


async def create_db_pool_with_retry():
    for attempt in range(10):
        try:
            logging.info(f"DB connect attempt {attempt + 1}")
            pool = await asyncpg.create_pool(
                user=os.getenv("POSTGRES_USER", "mlops"),
                password=os.getenv("POSTGRES_PASSWORD", "mlops"),
                database=os.getenv("POSTGRES_DB", "mlops"),
                host=os.getenv("POSTGRES_HOST", "postgres"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
            )
            logging.info("DB connection established")
            return pool
        except Exception as e:
            logging.warning(f"DB not ready: {e}")
            await asyncio.sleep(2)

    raise Exception("Could not connect to DB after retries")


# Connection to Postgres
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("LIFESPAN: creating DB pool")

    db.db_pool = await create_db_pool_with_retry()

    logging.info("LIFESPAN: DB pool created, starting worker")
    asyncio.create_task(worker_loop())
    logging.info("LIFESPAN: worker task started")

    yield

    logging.info("LIFESPAN: shutting down")
    await db.db_pool.close()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}
