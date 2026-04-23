import pytest


@pytest.mark.asyncio
async def test_train_unique_client(client):
    p1 = {"client_id": "a1", "dataset_name": "d", "dataset_id": 1}
    p2 = {"client_id": "a2", "dataset_name": "d", "dataset_id": 1}

    r1 = await client.post("/train", params=p1)
    r2 = await client.post("/train", params=p2)

    assert r1.json()["job_id"] != r2.json()["job_id"]
