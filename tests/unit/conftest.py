import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_db_pool():
    """Fixture for a mocked database pool."""
    mock = AsyncMock()
    # We want mock.acquire() to return an object that has __aenter__ and __aexit__.
    # Using MagicMock for acquire so that calling it returns the AsyncMock (the context manager).
    mock.acquire = MagicMock(return_value=AsyncMock())
    return mock


@pytest.fixture
def mock_minio_client():
    """Fixture for a mocked MinIO client."""
    return MagicMock()


@pytest.fixture
def mock_mlflow_client():
    """Fixture for a mocked MLflow client."""
    return MagicMock()


def create_test_job(job_id: str, name: str):
    return {"job_id": job_id, "name": name, "status": "PENDING"}


def create_test_dataset(dataset_id: str, name: str):
    return {"dataset_id": dataset_id, "name": name, "path": f"s3://test/{dataset_id}"}


def generate_test_input(data_type: str):
    if data_type == "image":
        return {"type": "image", "data": "binary_data_placeholder"}
    return {"type": "json", "data": {"key": "value"}}


@pytest.fixture
def sample_dataset():
    return create_test_dataset("ds-123", "sample_dataset")


@pytest.fixture
def sample_model():
    return {"model_id": "mod-456", "version": "1.0.0", "path": "s3://models/mod-456"}


@pytest.fixture
def sample_prediction_input():
    return generate_test_input("json")
