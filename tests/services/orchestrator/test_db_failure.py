import pytest


@pytest.mark.asyncio
async def test_db_failure(client):
    from services.orchestrator import app as app_module

    class FailingConn:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def fetchval(self, *args, **kwargs):
            raise Exception("DB is down")

        async def fetch(self, *args, **kwargs):
            raise Exception("DB is down")

        async def execute(self, *args, **kwargs):
            raise Exception("DB is down")

    class FailingPool:
        def acquire(self):
            return FailingConn()

    app_module.db_pool = FailingPool()

    r = await client.post(
        "/train",
        params={
            "client_id": "fail_user",
            "dataset_name": "data",
            "dataset_id": 1,
        },
    )

    assert r.status_code in (500, 503)
