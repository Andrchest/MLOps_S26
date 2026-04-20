import pytest
from unittest.mock import patch, MagicMock
import asyncio
from load_model import fetch_model_bytes, _MODEL_BYTES_CACHE


@pytest.mark.asyncio
async def test_fetch_model_bytes_cache_hit():
    # Setup: Pre-populate the cache
    model_name = "test_model"
    model_version = "v1"
    cache_key = f"{model_name}:{model_version}"
    dummy_bytes = b"cached_bytes"
    _MODEL_BYTES_CACHE[cache_key] = dummy_bytes

    # Test: Fetch from cache
    with patch("load_model.get_model_from_minio") as mock_minio:
        bytes_returned = await fetch_model_bytes(model_name, model_version)

        assert bytes_returned == dummy_bytes
        mock_minio.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_model_bytes_cache_miss():
    # Setup: Ensure cache is empty for this key
    model_name = "new_model"
    model_version = "v2"
    cache_key = f"{model_name}:{model_version}"
    if cache_key in _MODEL_BYTES_CACHE:
        del _MODEL_BYTES_CACHE[cache_key]

    dummy_bytes = b"new_model_bytes"

    # Test: Fetch from Minio and verify it gets cached
    with patch(
        "load_model.get_model_from_minio", return_value=dummy_bytes
    ) as mock_minio:
        bytes_returned = await fetch_model_bytes(model_name, model_version)

        assert bytes_returned == dummy_bytes
        mock_minio.assert_called_once_with(model_name, model_version)
        assert _MODEL_BYTES_CACHE[cache_key] == dummy_bytes


@pytest.mark.asyncio
async def test_fetch_model_bytes_error():
    model_name = "error_model"
    model_version = "v3"

    # Test: Handle error from Minio
    with patch(
        "load_model.get_model_from_minio",
        side_effect=Exception("Minio connection failed"),
    ):
        with pytest.raises(ValueError) as excinfo:
            await fetch_model_bytes(model_name, model_version)

        assert "not found in Minio" in str(excinfo.value)
        assert "Minio connection failed" in str(excinfo.value)
