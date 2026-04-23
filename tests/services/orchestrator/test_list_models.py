import pytest


@pytest.mark.asyncio
async def test_list_models(client):
    await client.post(
        "/models/promote",
        params={
            "model_name": "bert",
            "model_version": "v1",
            "deployed_by": "tester",
        },
    )

    r = await client.get("/models")

    assert "bert" in r.json()
