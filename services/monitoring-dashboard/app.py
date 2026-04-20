import streamlit as st

from db import check_db_health
from repository import (
    get_job_status_counts,
    get_jobs,
    get_models,
    get_recent_prediction_logs,
    get_total_jobs,
    get_total_models,
)
from ui import render_result

st.set_page_config(page_title="Monitoring Dashboard", page_icon="📊", layout="wide")

st.title("Monitoring Dashboard")
st.caption("Read-only dashboard for jobs, models, and overall system visibility.")

page = st.sidebar.radio("Navigate", ["System Overview", "Jobs", "Models"])

db_ok, db_error = check_db_health()

if not db_ok:
    st.error(f"Database unavailable: {db_error}")
    st.info("The dashboard is running, but DB-backed data cannot be loaded.")
    st.stop()

if page == "System Overview":
    st.header("System Overview")

    jobs_total = get_total_jobs()
    models_total = get_total_models()

    col1, col2 = st.columns(2)

    with col1:
        if jobs_total["ok"] and not jobs_total["data"].empty:
            st.metric("Total Jobs", int(jobs_total["data"].iloc[0]["total_jobs"]))
        else:
            st.warning("Unable to load jobs total.")

    with col2:
        if models_total["ok"] and not models_total["data"].empty:
            st.metric("Total Models", int(models_total["data"].iloc[0]["total_models"]))
        else:
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
    render_result(get_jobs(), "Jobs", "No jobs found.")

elif page == "Models":
    st.header("Models")
    render_result(get_models(), "Trained Models", "No models found.")
