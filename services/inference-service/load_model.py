from cachetools import LRUCache

# Initialize an LRU Cache with a max number of items
_MODEL_BYTES_CACHE = LRUCache(maxsize=10)


async def fetch_model_bytes(db_pool, model_name: str, model_version: str):
    cache_key = f"{model_name}:{model_version}"

    # Check cache
    if cache_key in _MODEL_BYTES_CACHE:
        return _MODEL_BYTES_CACHE[cache_key]

    async with db_pool.acquire() as conn:
        model_bytes = await conn.fetchval(
            """
            SELECT model
            FROM trained_models
            WHERE
                model_name = $1
                AND
                model_version = $2
            """,
            model_name,
            model_version,
        )
        if not model_bytes:
            raise ValueError(f"Model {model_name} v{model_version} not found")

        # Add to cache.
        # If full, the least recently used item is automatically removed.
        _MODEL_BYTES_CACHE[cache_key] = model_bytes
        return model_bytes
