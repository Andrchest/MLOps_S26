import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, patch, AsyncMock
import app
from schemas import InputData, Prediction, PredictResponse
from datetime import datetime
import uuid
import asyncio


@pytest.fixture
async def client():
    # We need to mock the db_pool and model_executor BEFORE the lifespan starts
    # Since AsyncClient(app=app) triggers lifespan, we must patch app.db_pool and app.model_executor

    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    mock_executor = MagicMock()

    with patch("app.db_pool", mock_pool, create=True), patch(
        "app.model_executor", mock_executor, create=True
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app.app), base_url="http://test"
        ) as ac:
            yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
@patch("app.fetch_model_bytes")
@patch("app.save_log")
async def test_predict_success(mock_save_log, mock_fetch_model, client):
    # Setup
    model_name = "test_model"
    model_version = "v1"
    input_data = {"age": 30, "monthly_spend": 100.0, "tenure_months": 12}

    # Mock fetch_model_bytes to return dummy bytes
    mock_fetch_model.return_value = b"dummy_bytes"

    # Mock the loop and its run_in_executor
    with patch("asyncio.get_running_loop") as mock_get_loop:
        mock_loop = MagicMock()
        # run_in_executor is NOT a coroutine, but we can make it an AsyncMock
        # so that 'await loop.run_in_executor(...)' works.
        mock_loop.run_in_executor = AsyncMock(return_value=(1, 0.8))
        mock_get_loop.return_value = mock_loop

        response = await client.post(
            f"/predict?model_name={model_name}&model_version={model_version}",
            json=input_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["model_name"] == model_name
        assert data["model_version"] == model_version
        assert data["prediction"]["label"] == 1
        assert data["prediction"]["score"] == 0.8
        assert data["status"] == "success"


@pytest.mark.asyncio
@patch("app.fetch_model_bytes")
@patch("app.save_log")
async def test_predict_not_found(mock_save_log, mock_fetch_model, client):
    # Setup
    model_name = "non_existent_model"
    model_version = "v1"
    input_data = {"age": 30, "monthly_spend": 100.0, "tenure_months": 12}

    # Mock fetch_model_bytes to raise ValueError
    mock_fetch_model.side_effect = ValueError("Model not found")

    response = await client.post(
        f"/predict?model_name={model_name}&model_version={model_version}",
        json=input_data,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Model not found"


@pytest.mark.asyncio
@patch("app.fetch_model_bytes")
@patch("app.save_log")
async def test_predict_error(mock_save_log, mock_fetch_model, client):
    # Setup
    model_name = "error_model"
    model_version = "v1"
    input_data = {"age": 30, "monthly_spend": 100.0, "tenure_months": 12}

    # Mock fetch_model_bytes to return dummy bytes
    mock_fetch_model.return_value = b"dummy_bytes"

    # Mock the loop and its run_in_executor
    with patch("asyncio.get_running_loop") as mock_get_loop:
        mock_loop = MagicMock()
        # Use AsyncMock so that it can be awaited and it raises the exception
        mock_loop.run_in_executor = AsyncMock(
            side_effect=Exception("Prediction failed")
        )
        mock_get_loop.return_value = mock_loop

        response = await client.post(
            f"/predict?model_name={model_name}&model_version={model_version}",
            json=input_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["prediction"]["label"] == 0
        assert data["prediction"]["score"] == 0.0
        assert "error:" in data["status"]


@pytest.mark.asyncio
@patch("asyncio.get_running_loop")
async def test_reload_endpoint(mock_get_loop, client):
    # Setup
    mock_loop = MagicMock()
    mock_get_loop.return_value = mock_loop

    response = await client.get("/reload")

    assert response.status_code == 200
    assert response.json() == {"status": "success"}

    # Verify loop.run_in_executor was called for shutdown
    assert mock_loop.run_in_executor.called
