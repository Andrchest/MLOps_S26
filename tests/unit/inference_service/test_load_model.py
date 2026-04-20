import sys
import pytest
import asyncio
from unittest.mock import patch

# Ensure the service directory is in the path
sys.path.append("/home/andreipc/MLOps/MLOps_S26/services/inference-service")

from load_model import fetch_model_bytes, _MODEL_BYTES_CACHE


@pytest.mark.asyncio
async def test_fetch_model_bytes_cache_hit():
    # Setup: Pre-populate cache
    model_name = "test_model"
    model_version = "v1"
    cache_key = f"{model_name}:{model_version}"
    model_bytes = b"fake_model_bytes"
    _MODEL_BYTES_CACHE[cache_key] = model_bytes

    # Execute
    with patch("load_model.get_model_from_minio") as mock_get:
        result = await fetch_model_bytes(model_name, model_version)

        # Verify
        assert result == model_bytes
        mock_get.assert_not_called()

    # Cleanup
    _MODEL_BYTES_CACHE.clear()


@pytest.mark.asyncio
async def test_fetch_model_bytes_cache_miss():
    # Setup: Ensure cache is empty
    _MODEL_BYTES_CACHE.clear()
    model_name = "test_model"
    model_version = "v1"
    model_bytes = b"fake_model_bytes"

    # Execute
    with patch("load_model.get_model_from_minio", return_value=model_bytes) as mock_get:
        result = await fetch_model_bytes(model_name, model_version)

        # Verify
        assert result == model_bytes
        mock_get.assert_called_once_with(model_name, model_version)
        assert f"{model_name}:{model_version}" in _MODEL_BYTES_CACHE

    # Cleanup
    _MODEL_BYTES_CACHE.clear()


@pytest.mark.asyncio
async def test_fetch_model_bytes_failure():
    # Setup: Ensure cache is empty
    _MODEL_BYTES_CACHE.clear()
    model_name = "test_model"
    model_version = "v1"

    # Execute
    with patch(
        "load_model.get_model_from_minio", side_effect=Exception("Minio error")
    ) as mock_get:
        with pytest.raises(
            ValueError,
            match="Model test_model/v1.joblib not found in Minio: Minio error",
        ):
            await fetch_model_bytes(model_name, model_version)

        mock_get.assert_called_once_with(model_name, model_version)

    # Cleanup
    _MODEL_BYTES_CACHE.clear()
