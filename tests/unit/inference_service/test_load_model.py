import sys
import pytest
import asyncio
from unittest.mock import patch, MagicMock

# Ensure the service directory is in the path
sys.path.append("/home/andreipc/MLOps/MLOps_S26/services/inference-service")

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

    mock_s3_error = MagicMock(spec=S3Error)
    mock_s3_error.code = "NoSuchKey"

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
