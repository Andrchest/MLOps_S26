import pytest


@pytest.mark.asyncio
async def test_rollback(client):
    await client.post(
        "/models/promote",
        params={"model_name": "bert", "model_version": "v1"},
    )

    await client.post(
        "/models/promote",
        params={"model_name": "bert", "model_version": "v2"},
    )

    r = await client.post("/models/rollback", params={"model_name": "bert"})

    assert r.status_code == 200
    assert r.json()["status"] == "rolled back"
