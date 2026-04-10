import asyncpg
import asyncio
import db
from fastapi import FastAPI
from contextlib import asynccontextmanager
from worker import worker_loop


# Connection to Postgres
@asynccontextmanager
async def lifespan(app: FastAPI):
    db.db_pool = await asyncpg.create_pool(
        user="mlops", password="mlops", database="mlops", host="postgres", port=5432
    )
    yield
    await db.db_pool.close()


app = FastAPI(lifespan=lifespan)


@app.on_event("startup")
async def start_worker():
    asyncio.create_task(worker_loop())
