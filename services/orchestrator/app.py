from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


global db_pool


@app.post("/train")
async def train(dataset_name: str, dataset_id: int):
    async with db_pool.acqure() as conn:
        job_id = await conn.fetchval(
            """
            INSERT INTO jobs (dataset_name, dataset_id, status)
            VALUES ($1, $2, 'pending')
            RETURNING job_id
            """,
            dataset_name,
            dataset_id,
        )

        return f"job_id: {job_id}"


@app.get("/jobs/job_id")
async def gut_status(job_id: int):
    async with db_pool.acqure() as conn:
        status = await conn.fetchval(
            """
            SELECT (status)
            from jobs
            WHERE job_id = $1
            """,
            job_id,
        )

        return f"status: {status}"


@app.post("/datasets")
def register_dataset():
    return {"status": "ok"}
