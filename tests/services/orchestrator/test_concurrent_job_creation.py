import asyncio
import pytest


@pytest.mark.asyncio
async def test_concurrent_job_creation(client):
    payload = {
        "client_id": "race123",
        "dataset_name": "data",
        "dataset_id": 1,
    }

    r1, r2 = await asyncio.gather(
        client.post("/train", params=payload),
        client.post("/train", params=payload),
    )

    assert r1.json()["job_id"] == r2.json()["job_id"]
