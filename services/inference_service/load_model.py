from cachetools import LRUCache
import asyncio
from services.inference_service.minio_client import get_model_from_minio
from tenacity import retry, stop_after_attempt, wait_exponential
from minio.error import S3Error

# Initialize an LRU Cache with a max number of items
_MODEL_BYTES_CACHE = LRUCache(maxsize=10)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=6))
async def fetch_model_with_retry(model_name, model_version):
    return await fetch_model_bytes(model_name, model_version)


async def fetch_model_bytes(model_name: str, model_version: str):
    """
    Fetches model bytes from Minio.
    """
    cache_key = f"{model_name}:{model_version}"

    if cache_key in _MODEL_BYTES_CACHE:
        return _MODEL_BYTES_CACHE[cache_key]

    object_name = f"{model_name}/{model_version}.joblib"

    try:
        # Run the synchronous Minio call in a thread to keep FastAPI responsive
        loop = asyncio.get_running_loop()

        model_bytes = await loop.run_in_executor(
            None, get_model_from_minio, model_name, model_version
        )

        _MODEL_BYTES_CACHE[cache_key] = model_bytes
        return model_bytes

    except S3Error as e:
        if e.code == "NoSuchKey":
            raise ValueError(f"Model {object_name} not found")

        raise
