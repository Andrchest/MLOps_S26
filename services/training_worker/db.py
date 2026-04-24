import json

db_pool = None


async def recover_stuck_jobs():
    import logging

    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE jobs
            SET status = 'pending'
            WHERE status = 'running'
        """)
    logging.info("Recovered stuck jobs")


async def get_job():
    async with db_pool.acquire() as conn:
        return await conn.fetchrow("""
            UPDATE jobs
            SET status = 'running'
            FROM datasets

            WHERE job_id = (
                SELECT job_id
                FROM jobs
                WHERE status = 'pending'
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            AND datasets.dataset_id = jobs.dataset_id
            RETURNING jobs.job_id, datasets.dataset_name, jobs.dataset_id
            """)


async def update_status(job_id, status):
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE jobs SET status=$1 WHERE job_id=$2", status, job_id)


async def save_trained_model(
    job_id: int,
    model_name: str,
    model_version: str,
    model_path: str,
    metrics: dict,
    parameters: dict,
):
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO trained_models
            (job_id, model_name, model_version, model_path, metrics, parameters)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            job_id,
            model_name,
            model_version,
            model_path,
            json.dumps(metrics),
            json.dumps(parameters),
        )
