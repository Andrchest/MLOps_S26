import pytest


@pytest.mark.asyncio
async def test_get_job_status(client):
    payload = {
        "client_id": "abc123",
        "dataset_name": "data",
        "dataset_id": 1,
    }

    r = await client.post("/train", params=payload)
    job_id = r.json()["job_id"]

    r2 = await client.get(f"/jobs/{job_id}")

    assert r2.json()["status"] == "pending"
