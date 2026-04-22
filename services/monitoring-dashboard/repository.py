from typing import Any

import pandas as pd
import requests

from db import get_connection


# ----------------------
# Core helper
# ----------------------
def safe_query_to_df(query: str) -> dict[str, Any]:
    try:
        with get_connection() as conn:
            df = pd.read_sql_query(query, conn)
        return {"ok": True, "data": df, "error": None}
    except Exception as exc:
        return {"ok": False, "data": pd.DataFrame(), "error": str(exc)}


# ----------------------
# Jobs
# ----------------------
def get_jobs():
    return safe_query_to_df("""
        SELECT job_id, dataset_name, dataset_id, status
        FROM jobs
        ORDER BY job_id DESC
        LIMIT 100
    """)


def get_job_status_counts():
    return safe_query_to_df("""
        SELECT status, COUNT(*) AS count
        FROM jobs
        GROUP BY status
        ORDER BY status
    """)


def get_total_jobs():
    return safe_query_to_df("SELECT COUNT(*) AS total_jobs FROM jobs")


# ----------------------
# Models
# ----------------------
def get_models():
    return safe_query_to_df("""
        SELECT job_id, model_name, model_version, model_path, metrics, parameters
        FROM trained_models
        ORDER BY job_id DESC
        LIMIT 100
    """)


def get_total_models():
    return safe_query_to_df("SELECT COUNT(*) AS total_models FROM trained_models")


# ----------------------
# Prediction Logs (Monitoring)
# ----------------------
def get_recent_prediction_logs():
    return safe_query_to_df("""
        SELECT request_id, timestamp, model_version, model_name, latency_ms, status
        FROM prediction_logs
        ORDER BY timestamp DESC
        LIMIT 20
    """)


def get_latency_stats():
    return safe_query_to_df("""
        SELECT
            AVG(latency_ms) AS avg_latency,
            MAX(latency_ms) AS max_latency,
            MIN(latency_ms) AS min_latency
        FROM prediction_logs
    """)


def get_prediction_status_distribution():
    return safe_query_to_df("""
        SELECT status, COUNT(*) AS count
        FROM prediction_logs
        GROUP BY status
    """)


# ----------------------
# Datasets (placeholder until backend ready)
# ----------------------
def get_datasets():
    # TODO: replace with real table or API
    return {
        "ok": True,
        "data": pd.DataFrame([
            {"dataset_id": 1, "name": "customer_churn.csv"},
            {"dataset_id": 2, "name": "fraud_data.csv"},
        ]),
        "error": None
    }


# ----------------------
# Deployments (placeholder)
# ----------------------
def get_deployments():
    return {
        "ok": True,
        "data": pd.DataFrame([
            {"deployment_id": 1, "model": "churn_model_v1", "status": "active"},
            {"deployment_id": 2, "model": "fraud_model_v2", "status": "inactive"},
        ]),
        "error": None
    }


# ----------------------
# System Health
# ----------------------
SERVICES = {
    "orchestrator": "http://localhost:8000/health",
    "inference": "http://localhost:8001/health",
    "monitoring": "http://localhost:8002/health",
}


def get_service_health():
    results = []

    for name, url in SERVICES.items():
        try:
            res = requests.get(url, timeout=2)
            status = "healthy" if res.status_code == 200 else "degraded"
        except Exception:
            status = "down"

        results.append({"service": name, "status": status})

    return {
        "ok": True,
        "data": pd.DataFrame(results),
        "error": None
    }