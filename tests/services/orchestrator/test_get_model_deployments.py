import pytest


@pytest.mark.asyncio
async def test_get_model_deployments(client):
    await client.post(
        "/models/promote",
        params={
            "model_name": "bert",
            "model_version": "v1",
            "deployed_by": "tester",
        },
    )

    r = await client.get("/models/bert/deployments")

    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1
