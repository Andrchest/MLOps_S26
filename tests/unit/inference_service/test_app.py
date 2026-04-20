import sys
import os
from pathlib import Path
import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Add the project root and the service directory to sys.path
project_root = Path("/home/andreipc/MLOps/MLOps_S26")
service_dir = project_root / "services" / "inference-service"
sys.path.append(str(project_root))
sys.path.append(str(service_dir))

try:
    import app
    from schemas import InputData, Prediction, PredictResponse
    from httpx import AsyncClient, ASGITransport
    APP_INSTANCE = app.app
    # For patching, we need the module name as it's seen by the system
    # Since we added service_dir to sys.path, it's just 'app'
    APP_MODULE_NAME = 'app'
    SCHEMA_MODULE_NAME = 'schemas'
except ImportError as e:
    print(f"Import error: {e}")
    # This might happen if fastapi/httpx are not installed
    raise

@pytest.mark.asyncio
async def test_health_ok():
    async with AsyncClient(transport=ASGITransport(app=APP_INSTANCE), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_reload_success():
    with patch(f"{APP_MODULE_NAME}.ProcessPoolExecutor") as mock_executor_cls,          patch(f"{APP_MODULE_NAME}.model_executor", MagicMock()) as mock_old_executor,          patch(f"{APP_MODULE_NAME}.reload_lock", asyncio.Lock()) as mock_lock:
        
        # Clear the bytes cache in the main process
        app._MODEL_BYTES_CACHE.clear()
        app._MODEL_BYTES_CACHE["test_key"] = b"test_bytes"

        async with AsyncClient(transport=ASGITransport(app=APP_INSTANCE), base_url="http://test") as ac:
            response = await ac.get("/reload")
        
        assert response.status_code == 200
        assert response.json() == {"status": "success"}
        assert len(app._MODEL_BYTES_CACHE) == 0

@pytest.mark.asyncio
@patch(f"{APP_MODULE_NAME}.fetch_model_bytes")
@patch(f"{APP_MODULE_NAME}.Predictor")
@patch(f"{APP_MODULE_NAME}.save_log", new_callable=AsyncMock)
@patch(f"{APP_MODULE_NAME}.db_pool", new_callable=MagicMock)
async def test_predict_success(
    mock_db_pool, 
    mock_save_log, 
    mock_predictor_class, 
    mock_fetch_model_bytes
):
    # Setup
    mock_fetch_model_bytes.return_value = b"dummy_bytes"
    
    mock_predictor_instance = mock_predictor_class.return_value
    mock_predictor_instance.predict.return_value = (1, 0.95)
    
    with patch(f"{APP_MODULE_NAME}.model_executor") as mock_executor:
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            
            async def mock_run_in_executor(executor, func, *args):
                return func(*args)
            
            mock_loop.run_in_executor.side_effect = mock_run_in_executor

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
            
            await asyncio.sleep(0.1)
            mock_save_log.assert_called_once()

@pytest.mark.asyncio
@patch(f"{APP_MODULE_NAME}.fetch_model_bytes")
async def test_predict_model_not_found(mock_fetch_model_bytes):
    mock_fetch_model_bytes.side_effect = ValueError("Model not found")
    
    async with AsyncClient(transport=ASGITransport(app=APP_INSTANCE), base_url="http://test") as ac:
        payload = {"age": 30, "monthly_spend": 100.0, "tenure_months": 12}
        response = await ac.post(
            "/predict?model_name=missing&model_version=v1",
            json=payload
        )
    
    assert response.status_code == 404

@pytest.mark.asyncio
@patch(f"{APP_MODULE_NAME}.fetch_model_bytes")
@patch(f"{APP_MODULE_NAME}.Predictor")
@patch(f"{APP_MODULE_NAME}.save_log", new_callable=AsyncMock)
async def test_predict_error(mock_save_log, mock_predictor_class, mock_fetch_model_bytes):
    mock_fetch_model_bytes.side_effect = Exception("Something went wrong")
    
    async with AsyncClient(transport=ASGITransport(app=APP_INSTANCE), base_url="http://test") as ac:
        payload = {"age": 30, "monthly_spend": 100.0, "tenure_months": 12}
        response = await ac.post(
            "/predict?model_name=test_model&model_version=v1",
            json=payload
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error: Something went wrong"
    assert data["prediction"]["label"] == 0
    assert data["prediction"]["score"] == 0.0
