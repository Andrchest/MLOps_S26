import asyncpg
import asyncio
import logging
import os
import sys
import db
from fastapi import FastAPI
from contextlib import asynccontextmanager
from worker import worker_loop

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")


# Connection to Postgres
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("LIFESPAN: creating DB pool")
    db.db_pool = await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER", "mlops"),
        password=os.getenv("POSTGRES_PASSWORD", "mlops"),
        database=os.getenv("POSTGRES_DB", "mlops"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )
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
