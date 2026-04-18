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


@app.post("/train/create")
async def train(dataset_id: int):
    async with db_pool.acquire() as conn:
        job_id = await conn.fetchval(
            """
            INSERT INTO jobs (dataset_id, status)
            VALUES ($1, 'pending')
            RETURNING job_id
            """,
            dataset_id,
        )

        return f"job_id: {job_id}"


@app.get("/jobs/{job_id}")
async def get_status(job_id: int):
    async with db_pool.acquire() as conn:
        status = await conn.fetchval(
            """
            SELECT (status)
            from jobs
            WHERE job_id = $1
            """,
            job_id,
        )

        return {"job_id": job_id, "status": status}


@app.post("/datasets")
async def register_dataset(dataset_id: int, dataset_name: str, dataset_version: str):
    async with db_pool.acquire() as conn:
        try:
            dataset = await conn.execute(
                """
                INSERT INTO datasets (dataset_id, dataset_name, dataset_version)
                VALUES ($1, $2, $3)
                RETURNING dataset_id, dataset_name
                """,
                dataset_id,
                dataset_name,
                dataset_version,
            )
            return f"register dataset: {dataset} OK"
        except BaseException as e:
            return f"FATAL: {e}"


@app.post("/models/promote")
async def promote_model(model_name: str, model_version: str):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT *
            FROM trained_models
            WHERE model_name=$1 AND model_version=$2
            """,
            model_name,
            model_version,
        )

    if not row:
        return {"error": "model not found"}

    await conn.execute(
        """
        INSERT INTO prod_models (model_name, model_version)
        VALUES ($1, $2)
        ON CONFLICT (model_name)
        DO UPDATE SET model_version = EXCLUDED.model_version
        """,
        row["model_name"],
        row["model_version"],
    )

    return {"status": "model promoted"}
