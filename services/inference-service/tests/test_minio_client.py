import pytest
from unittest.mock import MagicMock, patch
from minio_client import get_model_from_minio


@patch("minio_client.minio_client")
def test_get_model_from_minio(mock_minio_client):
    # Setup
    model_name = "test_model"
    model_version = "v1"
    bucket = "models"
    expected_object_name = "test_model/v1.joblib"
    expected_bytes = b"model_data"

    # Mock the response from get_object
    mock_response = MagicMock()
    mock_response.read.return_value = expected_bytes
    mock_minio_client.get_object.return_value = mock_response

    # Test
    bytes_returned = get_model_from_minio(model_name, model_version, bucket)

    # Verify
    assert bytes_returned == expected_bytes
    mock_minio_client.get_object.assert_called_once_with(bucket, expected_object_name)
    mock_response.close.assert_called_once()
    mock_response.release_conn.assert_called_once()


@patch("minio_client.minio_client")
def test_get_model_from_minio_error(mock_minio_client):
    # Setup
    model_name = "test_model"
    model_version = "v1"

    # Mock get_object to raise an exception
    mock_minio_client.get_object.side_effect = Exception("Minio error")

    # Test
    with pytest.raises(Exception) as excinfo:
        get_model_from_minio(model_name, model_version)

    assert "Minio error" in str(excinfo.value)
