import sys
import os
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from httpx import AsyncClient, ASGITransport

# Add the project root and the service directory to sys.path
project_root = Path("/home/andreipc/MLOps/MLOps_S26")
service_dir = project_root / "services" / "monitoring-service"
sys.path.append(str(project_root))
sys.path.append(str(service_dir))

try:
    import app

    APP_INSTANCE = app.app
    APP_MODULE_NAME = "app"
except ImportError as e:
    print(f"Import error: {e}")
    raise


@pytest.mark.asyncio
async def test_health_ok():
    async with AsyncClient(
        transport=ASGITransport(app=APP_INSTANCE), base_url="http://test"
    ) as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
@pytest.mark.skip(reason="Endpoint /metrics is not yet implemented")
async def test_metrics_stub():
    async with AsyncClient(
        transport=ASGITransport(app=APP_INSTANCE), base_url="http://test"
    ) as ac:
        response = await ac.get("/metrics")
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.skip(reason="Endpoint /drift is not yet implemented")
async def test_drift_stub():
    async with AsyncClient(
        transport=ASGITransport(app=APP_INSTANCE), base_url="http://test"
    ) as ac:
        response = await ac.get("/drift")
    assert response.status_code == 200
