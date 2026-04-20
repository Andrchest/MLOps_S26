import sys
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
    from services.inference_service.app import app
    from services.inference_service import load_model
    from httpx import AsyncClient, ASGITransport
except ImportError as e:
    print(f"Import error: {e}")
    raise


@pytest.fixture
def mock_model_executor():
    """Provide a mock model_executor for tests that need it."""
    from services.inference_service import app as app_mod

    with patch.object(app_mod, "model_executor", new_callable=lambda: MagicMock()) as mock:
        mock.run_in_executor = MagicMock(side_effect=lambda *a, **k: None)
        yield mock


@pytest.mark.asyncio
async def test_health_ok():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_reload_success():
    """Test that POST /reload clears cache and returns success."""
    from services.inference_service import app as app_mod

    # Initialize model_executor so reload has something to replace
    app_mod.model_executor = MagicMock()

    with patch.object(app_mod, "ProcessPoolExecutor", return_value=MagicMock()) as mock_executor_cls, \
         patch.object(app_mod, "reload_lock", new_callable=lambda: asyncio.Lock()):

        # Clear the bytes cache in the main process
        app_mod._MODEL_BYTES_CACHE.clear()
        app_mod._MODEL_BYTES_CACHE["test_key"] = b"test_bytes"

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post("/reload")

        assert response.status_code == 200
        assert response.json() == {"status": "success"}
        assert len(app_mod._MODEL_BYTES_CACHE) == 0


@pytest.mark.asyncio
async def test_predict_success():
    """Test successful prediction with mocked model loading and executor."""
    mock_model_bytes = b"dummy_model_bytes"

    async def mock_run(*args, **kwargs):
        return (1, 0.95)

    with patch.object(load_model, "fetch_model_with_retry", return_value=mock_model_bytes), \
         patch.object(load_model, "run_in_executor", new_callable=lambda: mock_run):

        from services.inference_service import app as app_mod
        app_mod.model_executor = MagicMock()
        app_mod.model_executor.run_in_executor = mock_run

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            payload = {"age": 30, "monthly_spend": 100.0, "tenure_months": 12}
            response = await ac.post(
                "/predict?model_name=test_model&model_version=v1", json=payload
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
    with patch.object(load_model, "fetch_model_with_retry", side_effect=ValueError("Model not found")):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            payload = {"age": 30, "monthly_spend": 100.0, "tenure_months": 12}
            response = await ac.post(
                "/predict?model_name=missing&model_version=v1", json=payload
            )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_predict_minio_unavailable():
    """Test that MinIO unavailability returns 503."""
    with patch.object(load_model, "fetch_model_with_retry", side_effect=Exception("MinIO connection failed")):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            payload = {"age": 30, "monthly_spend": 100.0, "tenure_months": 12}
            response = await ac.post(
                "/predict?model_name=test&model_version=v1", json=payload
            )

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_predict_prediction_crash():
    """Test that prediction logic crash returns 500."""
    mock_model_bytes = b"dummy_model_bytes"

    with patch.object(load_model, "fetch_model_with_retry", return_value=mock_model_bytes), \
         patch("services.inference_service.app._run_prediction", side_effect=Exception("Model prediction failed")):

        from services.inference_service import app as app_mod
        app_mod.model_executor = MagicMock()
        app_mod.model_executor.run_in_executor = MagicMock(side_effect=lambda *args: (1, 0.95))

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            payload = {"age": 30, "monthly_spend": 100.0, "tenure_months": 12}
            response = await ac.post(
                "/predict?model_name=test_model&model_version=v1", json=payload
            )

    assert response.status_code == 500
