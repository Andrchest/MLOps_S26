"""
Unit tests for training_worker/minio_client.py

These tests verify the MinIO download and upload functions.
Since minio_client.py creates a real Minio() instance at module load time,
we mock minio.Minio before importing the module.
"""

import sys
from unittest.mock import MagicMock, patch

# Mock minio module BEFORE importing minio_client, so the real Minio() constructor is never called
mock_minio_instance = MagicMock()
mock_minio_instance.fget_object = MagicMock()
mock_minio_instance.fput_object = MagicMock()
mock_minio_class = MagicMock(return_value=mock_minio_instance)
sys.modules["minio"] = MagicMock()
sys.modules["minio"].Minio = mock_minio_class

# Also mock minio_client to prevent the inference-service version from being loaded
fake_minio_client = MagicMock()
fake_minio_client.DATASETS_BUCKET = "datasets"
fake_minio_client.MODELS_BUCKET = "models"
fake_minio_client.minio_client = mock_minio_instance
sys.modules["minio_client"] = fake_minio_client

import pytest
from unittest.mock import MagicMock, patch
import os

# Add the services directory to sys.path so we can import from it
sys.path.insert(0, "/home/andreipc/MLOps/MLOps_S26/services/training_worker")
# Also add the root of the project to ensure imports work
sys.path.insert(0, "/home/andreipc/MLOps/MLOps_S26")

# Now reload minio_client to get the real training_worker version (with minio mocked)
del sys.modules["minio_client"]
import minio_client
from minio_client import download_dataset, save_model_to_minio


@patch.object(minio_client.minio_client, "fget_object")
def test_download_dataset(mock_fget):
    """Test that download_dataset calls fget_object with correct arguments."""
    download_dataset("test_dataset", "/tmp/test_data")
    mock_fget.assert_called_once_with(
        bucket_name=minio_client.DATASETS_BUCKET,
        object_name="test_dataset",
        file_path="/tmp/test_data",
    )


@patch.object(minio_client.minio_client, "fput_object")
@patch("os.path.exists")
def test_save_model_to_minio_success(mock_exists, mock_fput):
    """Test that save_model_to_minio uploads the model file to MinIO."""
    mock_exists.side_effect = lambda p: p == "/tmp/model/model.pkl"

    result = save_model_to_minio("/tmp/model", "my_model", "v1")

    expected_object_path = "my_model/v1.joblib"
    assert result == expected_object_path
    mock_fput.assert_called_once_with(
        bucket_name=minio_client.MODELS_BUCKET,
        object_name=expected_object_path,
        file_path="/tmp/model/model.pkl",
    )


@patch("os.path.exists")
def test_save_model_to_minio_not_found(mock_exists):
    """Test that save_model_to_minio raises FileNotFoundError when no model file exists."""
    mock_exists.return_value = False

    with pytest.raises(FileNotFoundError):
        save_model_to_minio("/tmp/model", "my_model", "v1")
