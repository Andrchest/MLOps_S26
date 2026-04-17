# Test configuration for integration tests
import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Test configuration values."""
    return {
        "base_url": "http://localhost",
        "orchestrator_port": 8000,
        "inference_port": 8001,
        "mlflow_port": 5000,
        "minio_port": 9000,
        "postgres_host": "localhost",
        "postgres_port": 5432,
        "postgres_user": "mlops",
        "postgres_password": "mlops",
        "postgres_db": "mlops",
    }
