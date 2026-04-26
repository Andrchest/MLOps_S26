import streamlit as st
import logging
from shared.utils.logging_utils import setup_logging
from asgi_correlation_id import correlation_id
import uuid
from services.monitoring_dashboard.db import check_db_health
from services.monitoring_dashboard.repository import *
from services.monitoring_dashboard.ui import render_result

logger = logging.getLogger(__name__)


# Set id into streamlt session
def inject_correlation_id():
    if "correlation_id" not in st.session_state:
        st.session_state.correlation_id = str(uuid.uuid4())
    correlation_id.set(st.session_state.correlation_id)
    logger.info("ID injected successfully", extra={"event": "session_start"})


setup_logging("monitoring-dashboard")
inject_correlation_id()

logger.info("Monitoring Dashboard started", extra={"event": "dashboard_started"})

st.set_page_config(page_title="Monitoring Dashboard", page_icon="📊", layout="wide")

st.title("Monitoring Dashboard")
st.caption("Read-only dashboard for jobs, models, and overall system visibility.")

page = st.sidebar.radio("Navigate", ["System Overview", "Jobs", "Models"])

db_ok, db_error = check_db_health()

if not db_ok:
    logger.error(
        "Database health check failed",
        extra={"event": "db_health_check_failed", "error": str(db_error)},
    )
    st.error(f"Database unavailable: {db_error}")
    st.info("The dashboard is running, but DB-backed data cannot be loaded.")
    st.stop()
else:
    logger.debug(
        "Database health check passed", extra={"event": "db_health_check_passed"}
    )

if page == "System Overview":
    st.header("System Overview")

    jobs_total = get_total_jobs()
    models_total = get_total_models()

    col1, col2 = st.columns(2)

    with col1:
        if jobs_total["ok"] and not jobs_total["data"].empty:
            logger.debug(
                "Successfully fetch total jobs", extra={"event": "fetch_jobs_success"}
            )
            st.metric("Total Jobs", int(jobs_total["data"].iloc[0]["total_jobs"]))
        else:
            logger.warning(
                "Failed to fetch total jobs", extra={"event": "fetch_jobs_failed"}
            )
            st.warning("Unable to load jobs total.")

    with col2:
        if models_total["ok"] and not models_total["data"].empty:
            logger.debug(
                "Successfully fetch total models",
                extra={"event": "fetch_models_success"},
            )
            st.metric("Total Models", int(models_total["data"].iloc[0]["total_models"]))
        else:
            logger.warning(
                "Failed to fetch total models", extra={"event": "fetch_models_failed"}
            )
            st.warning("Unable to load models total.")

    render_result(
        get_job_status_counts(),
        "Job Status Distribution",
        "No jobs available.",
    )

    render_result(
        get_recent_prediction_logs(),
        "Recent Prediction Logs",
        "No prediction logs available.",
    )

elif page == "Jobs":
    st.header("Jobs")
    result = get_jobs()
    if result["ok"]:
        logger.info("Jobs list loaded", extra={"event": "jobs_page_loaded"})
    else:
        logger.error("Failed to load jobs list", extra={"event": "jobs_page_failed"})
    render_result(result, "Jobs", "No jobs found.")

elif page == "Models":
    st.header("Models")
    models_result = get_models()

    if models_result["ok"]:
        logger.info(
            "Successfully fetched models list",
            extra={
                "event": "models_page_loaded",
                "count": len(models_result.get("data", [])),
            },
        )
    else:
        logger.error(
            "Failed to fetch models list",
            extra={"event": "models_page_failed", "error": models_result.get("error")},
        )

    render_result(models_result, "Trained Models", "No models found.")
