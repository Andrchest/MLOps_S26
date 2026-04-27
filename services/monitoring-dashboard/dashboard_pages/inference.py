import streamlit as st

from repository import (
    get_failed_predictions,
    get_latency_stats,
    get_recent_prediction_logs,
    get_successful_predictions,
    get_total_predictions,
)
from ui import render_status_badge, render_table


def get_scalar(result, column_name, fallback="—"):
    if result["ok"] and not result["data"].empty:
        value = result["data"].iloc[0][column_name]
        return fallback if value is None else value

    return fallback


def render_inference_card(title, value, caption, icon):
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


def render_empty_state():
    st.html(
        """
<div class="dashboard-card empty-state-card">
    <div class="empty-state-icon">⌁</div>
    <div class="empty-state-title">No predictions found</div>
    <div class="empty-state-text">
        Prediction logs will appear here after inference requests are made.
    </div>
</div>
"""
    )


def render_inference_page():
    st.markdown(
        """
<div class="page-section">
    <div class="page-eyebrow">Monitoring</div>
    <h2 class="page-title">Inference</h2>
    <p class="page-description">
        Monitor prediction volume, success rate, failures, latency, and recent inference activity.
    </p>
</div>
""",
        unsafe_allow_html=True,
    )

    total_predictions = get_total_predictions()
    successful_predictions = get_successful_predictions()
    failed_predictions = get_failed_predictions()
    latency_stats = get_latency_stats()

    total = get_scalar(total_predictions, "total_predictions")
    success = get_scalar(successful_predictions, "successful_predictions")
    failed = get_scalar(failed_predictions, "failed_predictions")
    avg_latency = get_scalar(latency_stats, "avg_latency")

    if avg_latency != "—":
        avg_latency = f"{round(float(avg_latency), 2)} ms"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_inference_card("Total Predictions", total, "All logged requests", "⌁")

    with col2:
        render_inference_card("Successful", success, "Completed predictions", "✓")

    with col3:
        render_inference_card("Failed", failed, "Requests with errors", "×")

    with col4:
        render_inference_card("Avg Latency", avg_latency, "Mean response time", "↯")

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    logs_result = get_recent_prediction_logs()

    if not logs_result["ok"]:
        render_table(
            logs_result,
            "Recent Predictions",
            "Unable to load prediction logs.",
        )
        return

    if logs_result["data"].empty:
        render_empty_state()
        return

    df = logs_result["data"].copy()

    st.markdown(
        """
<div class="dashboard-card table-card">
    <div class="card-title">Recent Predictions</div>
    <div class="card-subtitle">
        Latest inference requests with model version, status, and latency.
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    render_table(
        {"ok": True, "data": df, "error": None},
        "",
        "No predictions found.",
    )

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    selected_request = st.selectbox(
        "Select Prediction",
        df["request_id"].tolist(),
    )

    selected = df[df["request_id"] == selected_request].iloc[0]

    st.html(
        f"""
<div class="dashboard-card detail-card">
    <div class="detail-header">
        <div>
            <div class="card-title">Prediction Request</div>
            <div class="card-subtitle">{selected["request_id"]}</div>
        </div>
        <div class="status-pill">
            {render_status_badge(selected["status"])}
        </div>
    </div>

    <div class="detail-grid">
        <div class="detail-item">
            <div class="detail-label">Request ID</div>
            <div class="detail-value">{selected["request_id"]}</div>
        </div>

        <div class="detail-item">
            <div class="detail-label">Model</div>
            <div class="detail-value">{selected["model_name"]}</div>
        </div>

        <div class="detail-item">
            <div class="detail-label">Version</div>
            <div class="detail-value">{selected["model_version"]}</div>
        </div>

        <div class="detail-item">
            <div class="detail-label">Latency</div>
            <div class="detail-value">{selected["latency_ms"]} ms</div>
        </div>
    </div>
</div>
"""
    )