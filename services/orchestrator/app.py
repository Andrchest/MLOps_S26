from fastapi import FastAPI
import asyncpg
import os

app = FastAPI()

db_pool = None


async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER", "mlops"),
        password=os.getenv("POSTGRES_PASSWORD", "mlops"),
        database=os.getenv("POSTGRES_DB", "mlops"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )


@app.on_event("startup")
async def startup():
    await init_db()


@app.on_event("shutdown")
async def shutdown():
    await db_pool.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/train")
async def train(dataset_name: str, dataset_id: int):
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

        return {"job_id": job_id, "status": "pending"}


@app.get("/jobs/{job_id}")
async def get_status(job_id: int):
    async with db_pool.acquire() as conn:
        status = await conn.fetchval(
            """
            SELECT status FROM jobs WHERE job_id = $1
            """,
            job_id,
        )

        return {"job_id": job_id, "status": status}


@app.post("/datasets")
def register_dataset():
    return {"status": "ok"}
