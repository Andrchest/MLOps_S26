import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch
from services.orchestrator.app import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def mock_db_pool():
    from unittest.mock import MagicMock

    with patch(
        "services.orchestrator.app.db_pool", new_callable=MagicMock
    ) as mocked_pool:
        yield mocked_pool


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_train_success(client, mock_db_pool):
    # Mock the connection and fetchval
    mock_conn = AsyncMock()
    mock_conn.fetchval.return_value = 123
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    response = await client.post("/train?dataset_name=test_dataset&dataset_id=1")

    assert response.status_code == 200
    assert response.json() == {"job_id": 123, "status": "pending"}
    mock_conn.fetchval.assert_called_once()


@pytest.mark.asyncio
async def test_train_invalid_data(client):
    # Missing dataset_id
    response = await client.post("/train?dataset_name=test_dataset")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_job_success(client, mock_db_pool):
    mock_conn = AsyncMock()
    mock_conn.fetchval.return_value = "running"
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    response = await client.get("/jobs/123")

    assert response.status_code == 200
    assert response.json() == {"job_id": 123, "status": "running"}


@pytest.mark.asyncio
async def test_get_job_not_found(client, mock_db_pool):
    mock_conn = AsyncMock()
    mock_conn.fetchval.return_value = None
    mock_db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    response = await client.get("/jobs/999")

    assert response.status_code == 200
    assert response.json() == {"job_id": 999, "status": None}


@pytest.mark.skip(reason="Boilerplate for datasets endpoint")
@pytest.mark.asyncio
async def test_register_dataset(client):
    response = await client.post("/datasets")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
