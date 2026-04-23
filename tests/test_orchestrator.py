import asyncio
import asyncpg

DB_URL = "postgresql://postgres:postgres@localhost:5432/postgres"


async def setup_db(conn):
    await conn.execute("""
    DROP TABLE IF EXISTS trained_models;
    DROP TABLE IF EXISTS jobs;
    DROP TABLE IF EXISTS datasets;

    CREATE TABLE datasets (
        dataset_id INT PRIMARY KEY,
        dataset_name TEXT NOT NULL,
        dataset_version TEXT NOT NULL
    );

    CREATE TABLE jobs (
        job_id SERIAL PRIMARY KEY,
        dataset_id INT NOT NULL REFERENCES datasets(dataset_id),
        status TEXT DEFAULT 'pending'
    );

    CREATE TABLE trained_models (
        job_id INT NOT NULL REFERENCES jobs(job_id),
        model_name TEXT NOT NULL,
        model_version TEXT NOT NULL,
        model_path TEXT NOT NULL,
        metrics JSONB NOT NULL,
        parameters JSONB NOT NULL,
        created_at TIMESTAMP DEFAULT now(),
        PRIMARY KEY (job_id, model_version)
    );
    """)


async def train(conn):
    return await conn.fetchval("""
        INSERT INTO jobs (dataset_id, status)
        VALUES ($2, 'pending')
        RETURNING job_id
        """)


async def get_status(job_id: int):
    status = await conn.fetchval(
        """
            SELECT (status)
            from jobs
            WHERE job_id = $1
            """,
        job_id,
    )


async def register_dataset(dataset_id: int, dataset_name: str, dataset_version: str):
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


class PromoteRequest(BaseModel):
    job_id: int
    model_version: str


async def promote_model(req: PromoteRequest):
    row = await conn.fetchrow(
        """
            SELECT *
            FROM trained_models
            WHERE job_id=$1 AND model_version=$2
            """,
        req.job_id,
        req.model_version,
    )


async def test_orchestrator():
    conn = await asyncpg.connect(DB_URL)

    print("🔧 Создаём таблицы...")
    await setup_db(conn)

    print("🌱 Засеиваем данные...")
    await seed_data(conn)

    print("🚀 Берём job...")
    job = await get_job(conn)
    print("JOB:", job)

    assert job is not None, "❌ Job не вернулся"
    assert job["dataset_name"] == "test_dataset"

    status = await conn.fetchval(
        "SELECT status FROM jobs WHERE job_id = $1", job["job_id"]
    )
    print("STATUS:", status)

    assert status == "running", "❌ Статус не обновился"

    print("🧪 Тест на гонку...")
    job1, job2 = await asyncio.gather(get_job(conn), get_job(conn))
    print("JOB1:", job1)
    print("JOB2:", job2)

    assert (job1 is None) or (job2 is None), "❌ Две задачи взялись одновременно"

    await conn.close()
    print("✅ ВСЁ РАБОТАЕТ")


if __name__ == "__main__":
    asyncio.run(test_orchestrator())
