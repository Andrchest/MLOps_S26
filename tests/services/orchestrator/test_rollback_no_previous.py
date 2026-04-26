import pytest


@pytest.mark.asyncio
async def test_rollback_no_previous(client):
    await client.post(
        "/models/promote",
        params={"model_name": "bert", "model_version": "v1"},
    )

    r = await client.post("/models/rollback", params={"model_name": "bert"})

    assert "error" in r.json()
