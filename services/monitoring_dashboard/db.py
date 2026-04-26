import asyncio
import logging
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

import psycopg2
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)

logger = logging.getLogger(__name__)


def get_db_config() -> dict:
    return {
        "host": os.getenv("POSTGRES_HOST", "postgres"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "dbname": os.getenv("POSTGRES_DB", "mlops"),
        "user": os.getenv("POSTGRES_USER", "mlops"),
        "password": os.getenv("POSTGRES_PASSWORD", "mlops"),
    }


async def create_db_connection_with_retry(max_retries=10, retry_delay=2):
    for attempt in range(max_retries):
        try:
            logger.info(f"Creating DB connection (attempt {attempt + 1}/{max_retries})")
            conn = psycopg2.connect(**get_db_config())
            cur = conn.cursor()
            cur.execute("SELECT 1;")
            cur.close()
            logger.info("DB connection established successfully")
            return conn
        except Exception as e:
            logger.warning(f"DB connection failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                raise Exception(f"Could not connect to DB after {max_retries} attempts")


@contextmanager
def get_connection() -> Generator:
    conn = None
    try:
        conn = psycopg2.connect(**get_db_config())
        yield conn
    finally:
        if conn is not None:
            conn.close()


def check_db_health() -> tuple[bool, Optional[str]]:
    max_retries = 5
    for attempt in range(max_retries):
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    cur.fetchone()
            logger.info("DB health check passed")
            return True, None
        except Exception as exc:
            logger.warning(f"DB health check failed (attempt {attempt + 1}/{max_retries}): {exc}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return False, str(exc)
    return False, "Max retries exceeded"
