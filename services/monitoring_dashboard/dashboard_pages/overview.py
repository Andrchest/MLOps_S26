import streamlit as st

from repository import (
    get_job_status_counts,
    get_recent_prediction_logs,
    get_service_health,
    get_total_jobs,
    get_total_models,
)
from ui import render_table


def render_stat_card(title, value, caption, icon):
    st.markdown(
        f"""
        <div class="dashboard-card stat-card">
            <div class="stat-icon">{icon}</div>
            <div class="stat-value">{value}</div>
            <div class="stat-title">{title}</div>
            <div class="stat-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_card(status_type, title, message):
    st.markdown(
        f"""
        <div class="dashboard-card status-card status-{status_type}">
            <div>
                <div class="status-title">{title}</div>
                <div class="status-message">{message}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overview_page():
    st.markdown(
        """
        <div class="page-section">
            <div class="page-eyebrow">Overview</div>
            <h2 class="page-title">System Overview</h2>
            <p class="page-description">
                High-level visibility into jobs, models, predictions, and service health.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    health = get_service_health()
    jobs_total = get_total_jobs()
    models_total = get_total_models()

    if jobs_total["ok"] and not jobs_total["data"].empty:
        total_jobs = int(jobs_total["data"].iloc[0]["total_jobs"])
    else:
        total_jobs = "—"

    if models_total["ok"] and not models_total["data"].empty:
        total_models = int(models_total["data"].iloc[0]["total_models"])
    else:
        total_models = "—"

    if health["ok"] and not health["data"].empty:
        statuses = health["data"]["status"].tolist()

        if "down" in statuses:
            status_type = "down"
            status_title = "Service issue detected"
            status_message = "Some services are currently down and need attention."
        elif "degraded" in statuses:
            status_type = "degraded"
            status_title = "System degraded"
            status_message = "Some services are running with degraded performance."
        else:
            status_type = "healthy"
            status_title = "All systems operational"
            status_message = "All monitored services are healthy and available."
    else:
        status_type = "unknown"
        status_title = "System status unavailable"
        status_message = "Unable to load service health data."

    render_status_card(status_type, status_title, status_message)

    col1, col2, col3 = st.columns(3)

    with col1:
        render_stat_card(
            "Total Jobs",
            total_jobs,
            "Training and processing jobs",
            "☷",
        )

    with col2:
        render_stat_card(
            "Total Models",
            total_models,
            "Registered trained models",
            "◇",
        )

    with col3:
        if health["ok"] and not health["data"].empty:
            service_count = len(health["data"])
        else:
            service_count = "—"

        render_stat_card(
            "Services",
            service_count,
            "Tracked system services",
            "◌",
        )

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="dashboard-card table-card">
            <div class="card-header">
                <div>
                    <div class="card-title">Job Status Distribution</div>
                    <div class="card-subtitle">Current breakdown of job states.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_table(
        get_job_status_counts(),
        "",
        "No jobs available.",
    )

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="dashboard-card table-card">
            <div class="card-header">
                <div>
                    <div class="card-title">Recent Prediction Logs</div>
                    <div class="card-subtitle">Latest inference requests and prediction activity.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_table(
        get_recent_prediction_logs(),
        "",
        "No prediction logs available.",
    )