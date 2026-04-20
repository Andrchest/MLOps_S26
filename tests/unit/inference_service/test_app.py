import sys
import os
from pathlib import Path
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add the project root and the service directory to sys.path
project_root = Path(__file__).parent.parent.parent
service_dir = project_root / "services" / "inference_service"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(service_dir))

try:
    import app
    from schemas import InputData, Prediction, PredictResponse
    from httpx import AsyncClient, ASGITransport
    APP_INSTANCE = app.app
    APP_MODULE_NAME = 'app'
    SCHEMA_MODULE_NAME = 'schemas'
except ImportError as e:
    print(f"Import error: {e}")
    raise


@pytest.fixture
def mock_model_executor():
    """Provide a mock model_executor for tests that need it."""
    with patch(f"{APP_MODULE_NAME}.model_executor") as mock:
        mock.run_in_executor = MagicMock(side_effect=lambda *a, **k: None)
        yield mock


@pytest.mark.asyncio
async def test_health_ok():
    async with AsyncClient(transport=ASGITransport(app=APP_INSTANCE), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_reload_success():
    """Test that POST /reload clears cache and returns success."""
    from services.inference_service import app as app_mod
    # Initialize model_executor so reload has something to replace
    app_mod.model_executor = MagicMock()
    
    with patch(f"{APP_MODULE_NAME}.ProcessPoolExecutor") as mock_executor_cls, \
         patch(f"{APP_MODULE_NAME}.reload_lock", asyncio.Lock()):
        
        mock_executor_cls.return_value = MagicMock()
        
        # Clear the bytes cache in the main process
        app_mod._MODEL_BYTES_CACHE.clear()
        app_mod._MODEL_BYTES_CACHE["test_key"] = b"test_bytes"

        async with AsyncClient(transport=ASGITransport(app=APP_INSTANCE), base_url="http://test") as ac:
            response = await ac.post("/reload")
        
        assert response.status_code == 200
        assert response.json() == {"status": "success"}
        assert len(app_mod._MODEL_BYTES_CACHE) == 0


@pytest.mark.asyncio
async def test_predict_success():
    """Test successful prediction with mocked model loading and executor."""
    mock_model_bytes = b"dummy_model_bytes"
    
    with patch("load_model.fetch_model_with_retry", return_value=mock_model_bytes), \
         patch("app._run_prediction", return_value=(1, 0.95)), \
         patch(f"{APP_MODULE_NAME}.model_executor") as mock_executor:
        
        mock_loop = MagicMock()
        mock_executor.run_in_executor = MagicMock(
            side_effect=lambda *args: (1, 0.95)
        )
        
        with patch("asyncio.get_running_loop", return_value=mock_loop):
            async with AsyncClient(transport=ASGITransport(app=APP_INSTANCE), base_url="http://test") as ac:
                payload = {
                    "age": 30,
                    "monthly_spend": 100.0,
                    "tenure_months": 12
                }
                response = await ac.post(
                    "/predict?model_name=test_model&model_version=v1",
                    json=payload
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["model_name"] == "test_model"
        assert data["model_version"] == "v1"
        assert data["prediction"]["label"] == 1
        assert data["prediction"]["score"] == 0.95


@pytest.mark.asyncio
async def test_predict_model_not_found():
    """Test that missing model returns 404."""
    with patch("load_model.fetch_model_with_retry", side_effect=ValueError("Model not found")):
        async with AsyncClient(transport=ASGITransport(app=APP_INSTANCE), base_url="http://test") as ac:
            payload = {"age": 30, "monthly_spend": 100.0, "tenure_months": 12}
            response = await ac.post(
                "/predict?model_name=missing&model_version=v1",
                json=payload
            )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_predict_minio_unavailable():
    """Test that MinIO unavailability returns 503."""
    with patch("load_model.fetch_model_with_retry", side_effect=Exception("MinIO connection failed")):
        async with AsyncClient(transport=ASGITransport(app=APP_INSTANCE), base_url="http://test") as ac:
            payload = {"age": 30, "monthly_spend": 100.0, "tenure_months": 12}
            response = await ac.post(
                "/predict?model_name=test&model_version=v1",
                json=payload
            )
    
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_predict_prediction_crash():
    """Test that prediction logic crash returns 500."""
    mock_model_bytes = b"dummy_model_bytes"
    
    with patch("load_model.fetch_model_with_retry", return_value=mock_model_bytes), \
         patch("app._run_prediction", side_effect=Exception("Model prediction failed")):
        
        async with AsyncClient(transport=ASGITransport(app=APP_INSTANCE), base_url="http://test") as ac:
            payload = {"age": 30, "monthly_spend": 100.0, "tenure_months": 12}
            response = await ac.post(
                "/predict?model_name=test_model&model_version=v1",
                json=payload
            )
    
    assert response.status_code == 500
