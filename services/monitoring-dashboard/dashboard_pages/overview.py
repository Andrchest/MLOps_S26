import streamlit as st

from repository import (
    get_job_status_counts,
    get_recent_prediction_logs,
    get_service_health,
    get_total_jobs,
    get_total_models,
)
from ui import render_metric, render_table


def render_overview_page():
    st.header("System Overview")
    st.caption("High-level view of jobs, models, predictions, and system status.")

    health = get_service_health()

    if health["ok"] and not health["data"].empty:
        statuses = health["data"]["status"].tolist()

        st.markdown("### System Status")

        if "down" in statuses:
            st.error("Some services are down.")
        elif "degraded" in statuses:
            st.warning("Some services are degraded.")
        else:
            st.success("All systems operational.")

    st.divider()

    st.markdown("### Key Metrics")

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

    st.divider()

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