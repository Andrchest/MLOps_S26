from typing import Any

import pandas as pd

from db import get_connection


def safe_query_to_df(query: str) -> dict[str, Any]:
    try:
        with get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        return {"ok": True, "data": df, "error": None}
    except Exception as exc:
        return {"ok": False, "data": pd.DataFrame(), "error": str(exc)}


def get_jobs() -> dict[str, Any]:
    return safe_query_to_df("""
        SELECT job_id, dataset_name, dataset_id, status
        FROM jobs
        ORDER BY job_id DESC
        LIMIT 100
        """)


def get_job_status_counts() -> dict[str, Any]:
    return safe_query_to_df("""
        SELECT status, COUNT(*) AS count
        FROM jobs
        GROUP BY status
        ORDER BY status
        """)


def get_models() -> dict[str, Any]:
    return safe_query_to_df("""
        SELECT job_id, model_name, model_version, model_path, metrics, parameters
        FROM trained_models
        ORDER BY job_id DESC
        LIMIT 100
        """)


def get_total_jobs() -> dict[str, Any]:
    return safe_query_to_df("SELECT COUNT(*) AS total_jobs FROM jobs")


def get_total_models() -> dict[str, Any]:
    return safe_query_to_df("SELECT COUNT(*) AS total_models FROM trained_models")


def get_recent_prediction_logs() -> dict[str, Any]:
    return safe_query_to_df("""
        SELECT request_id, timestamp, model_version, model_name, latency_ms, status
        FROM prediction_logs
        ORDER BY timestamp DESC
        LIMIT 20
        """)
