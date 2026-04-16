import pytest
from contextlib import asynccontextmanager

import services.training_worker.db as db_module


# -------------------------
# FAKE DB LAYER
# -------------------------
class FakeConn:
    def __init__(self):
        self.executed = []

    async def fetchrow(self, *args, **kwargs):
        return {
            "job_id": 1,
            "dataset_name": "test.csv",
            "dataset_id": 1,
        }

    async def execute(self, query, *args, **kwargs):
        self.executed.append((query, args))


class FakePool:
    @asynccontextmanager
    async def acquire(self):
        yield FakeConn()


# -------------------------
# TESTS
# -------------------------
@pytest.mark.asyncio
async def test_get_job():
    db_module.db_pool = FakePool()

    result = await db_module.get_job()

    assert result["job_id"] == 1
    assert result["dataset_name"] == "test.csv"


@pytest.mark.asyncio
async def test_update_status():
    db_module.db_pool = FakePool()

    await db_module.update_status(1, "running")


@pytest.mark.asyncio
async def test_save_trained_model():
    db_module.db_pool = FakePool()

    await db_module.save_trained_model(
        job_id=1,
        model_name="model",
        model_version="v1",
        model_path="/tmp/model.joblib",
        metrics={"acc": 0.9},
        parameters={"lr": 0.01},
    )
