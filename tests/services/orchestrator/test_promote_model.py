import pytest


@pytest.mark.asyncio
async def test_promote_model(client):
    r = await client.post(
        "/models/promote",
        params={
            "model_name": "bert",
            "model_version": "v1",
            "deployed_by": "tester",
        },
    )

    assert r.status_code == 200
    assert r.json()["status"] == "promoted"
