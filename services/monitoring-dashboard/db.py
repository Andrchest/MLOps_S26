import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

import psycopg2
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH, override=True)


def get_db_config() -> dict:
    return {
        "host": os.getenv("POSTGRES_HOST", "postgres"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "dbname": os.getenv("POSTGRES_DB", "mlops"),
        "user": os.getenv("POSTGRES_USER", "mlops"),
        "password": os.getenv("POSTGRES_PASSWORD", "mlops"),
    }


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
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return True, None
    except Exception as exc:
        return False, str(exc)
