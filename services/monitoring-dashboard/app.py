import streamlit as st

from db import check_db_health
from repository import (
    get_job_status_counts,
    get_jobs,
    get_models,
    get_recent_prediction_logs,
    get_total_jobs,
    get_total_models,
    get_datasets,
    get_deployments,
    get_latency_stats,
    get_prediction_status_distribution,
    get_service_health,
)
from ui import render_table, render_metric, render_health_table

st.set_page_config(page_title="Monitoring Dashboard", page_icon="📊", layout="wide")

st.title("Monitoring Dashboard")
st.caption("Read-only dashboard for jobs, models, and overall system visibility.")

page = st.sidebar.radio(
    "Navigate",
    [
        "System Overview",
        "Jobs",
        "Datasets",
        "Models",
        "Deployments",
        "Monitoring",
        "System Health",
    ],
)

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
            render_metric("Total Jobs", int(jobs_total["data"].iloc[0]["total_jobs"]))
        else:
            st.warning("Unable to load jobs total.")

    with col2:
        if models_total["ok"] and not models_total["data"].empty:
            render_metric(
                "Total Models",
                int(models_total["data"].iloc[0]["total_models"]),
            )
        else:
            st.warning("Unable to load models total.")

    render_table(
        get_job_status_counts(),
        "Job Status Distribution",
        "No jobs available.",
    )

    render_table(
        get_recent_prediction_logs(),
        "Recent Prediction Logs",
        "No prediction logs available.",
    )

elif page == "Jobs":
    st.header("Jobs")
    render_table(get_jobs(), "Jobs", "No jobs found.")

elif page == "Datasets":
    st.header("Datasets")
    render_table(get_datasets(), "Datasets", "No datasets found.")

elif page == "Models":
    st.header("Models")
    render_table(get_models(), "Trained Models", "No models found.")

elif page == "Deployments":
    st.header("Deployments")
    render_table(get_deployments(), "Deployments", "No deployments found.")

elif page == "Monitoring":
    st.header("Monitoring")

    latency_stats = get_latency_stats()
    prediction_status = get_prediction_status_distribution()

    if latency_stats["ok"] and not latency_stats["data"].empty:
        stats_row = latency_stats["data"].iloc[0]
        col1, col2, col3 = st.columns(3)
        with col1:
            render_metric(
                "Avg Latency (ms)",
                round(float(stats_row["avg_latency"]), 2)
                if stats_row["avg_latency"] is not None
                else "N/A",
            )
        with col2:
            render_metric(
                "Max Latency (ms)",
                round(float(stats_row["max_latency"]), 2)
                if stats_row["max_latency"] is not None
                else "N/A",
            )
        with col3:
            render_metric(
                "Min Latency (ms)",
                round(float(stats_row["min_latency"]), 2)
                if stats_row["min_latency"] is not None
                else "N/A",
            )
    else:
        st.warning("Unable to load latency statistics.")

    render_table(
        prediction_status,
        "Prediction Status Distribution",
        "No prediction status data found.",
    )

    render_table(
        get_recent_prediction_logs(),
        "Recent Prediction Logs",
        "No prediction logs available.",
    )

elif page == "System Health":
    st.header("System Health")
    render_health_table(get_service_health())