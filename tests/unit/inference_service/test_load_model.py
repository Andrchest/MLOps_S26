import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure the service directory is in the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "services" / "inference_service"))

from load_model import fetch_model_bytes, _MODEL_BYTES_CACHE
from minio.error import S3Error


@pytest.mark.asyncio
async def test_fetch_model_bytes_cache_hit():
    model_name = "test_model"
    model_version = "v1"
    cache_key = f"{model_name}:{model_version}"
    model_bytes = b"fake_model_bytes"
    _MODEL_BYTES_CACHE[cache_key] = model_bytes

    with patch("load_model.get_model_from_minio") as mock_get:
        result = await fetch_model_bytes(model_name, model_version)

        assert result == model_bytes
        mock_get.assert_not_called()

    _MODEL_BYTES_CACHE.clear()


@pytest.mark.asyncio
async def test_fetch_model_bytes_cache_miss():
    _MODEL_BYTES_CACHE.clear()
    model_name = "test_model"
    model_version = "v1"
    model_bytes = b"fake_model_bytes"

    with patch("load_model.get_model_from_minio", return_value=model_bytes) as mock_get:
        result = await fetch_model_bytes(model_name, model_version)

        assert result == model_bytes
        mock_get.assert_called_once_with(model_name, model_version)
        assert f"{model_name}:{model_version}" in _MODEL_BYTES_CACHE

    _MODEL_BYTES_CACHE.clear()


@pytest.mark.asyncio
async def test_fetch_model_bytes_not_found_raises_value_error():
    _MODEL_BYTES_CACHE.clear()
    model_name = "test_model"
    model_version = "v1"

    # Create a mock HTTPResponse for S3Error
    from http.client import HTTPResponse
    from io import BytesIO

    mock_response = MagicMock()
    mock_response.status = 404
    mock_response.reason = "Not Found"
    mock_response.getheaders = MagicMock(return_value=[("x-amz-request-id", "test-id")])
    mock_response.read = MagicMock(return_value=b'{"code":"NoSuchKey"}')

    mock_s3_error = S3Error(
        response=mock_response,
        code="NoSuchKey",
        message="Not Found",
        resource="/models/test.joblib",
        request_id="test",
        host_id="test-host",
        bucket_name="models",
        object_name="test.joblib",
    )

    with patch("load_model.get_model_from_minio", side_effect=mock_s3_error):
        with pytest.raises(ValueError, match="Model test_model/v1.joblib not found"):
            await fetch_model_bytes(model_name, model_version)

    _MODEL_BYTES_CACHE.clear()


@pytest.mark.asyncio
async def test_fetch_model_bytes_other_error_propagates():
    _MODEL_BYTES_CACHE.clear()
    model_name = "test_model"
    model_version = "v1"

    with patch(
        "load_model.get_model_from_minio", side_effect=Exception("Network error")
    ):
        with pytest.raises(Exception, match="Network error"):
            await fetch_model_bytes(model_name, model_version)

    _MODEL_BYTES_CACHE.clear()
