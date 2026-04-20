import asyncio
import logging


# Retrying async functions
async def async_retry(
    func,
    *args,
    retries=3,
    delay=2,
    backoff=2,
    exceptions=(Exception,),
    **kwargs,
):
    current_delay = delay

    for attempt in range(retries):
        try:
            return await func(*args, **kwargs)
        except exceptions as e:
            if attempt == retries - 1:
                raise
            logging.warning(
                f"Retry {attempt + 1}/{retries} failed: {e}, retrying in {current_delay}s"
            )
            await asyncio.sleep(current_delay)
            current_delay *= backoff


# Retrying sync functions
def sync_retry(
    func, *args, retries=3, delay=2, backoff=2, exceptions=(Exception,), **kwargs
):
    import time

    current_delay = delay

    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            if attempt == retries - 1:
                raise
            logging.warning(
                f"Retry {attempt + 1}/{retries} failed: {e}, retrying in {current_delay}s"
            )
            time.sleep(current_delay)
            current_delay *= backoff
