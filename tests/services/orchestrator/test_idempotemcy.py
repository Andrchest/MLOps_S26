import pytest


@pytest.mark.asyncio
async def test_train_idempotency(client):
    payload = {
        "client_id": "abc123",
        "dataset_name": "data",
        "dataset_id": 1,
    }

    r1 = await client.post("/train", params=payload)
    r2 = await client.post("/train", params=payload)

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["job_id"] == r2.json()["job_id"]
