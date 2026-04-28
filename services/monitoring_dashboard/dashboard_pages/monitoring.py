import pandas as pd
import streamlit as st

from repository import (
    get_failed_predictions,
    get_latency_stats,
    get_prediction_status_distribution,
    get_prediction_trend,
    get_recent_prediction_logs,
    get_successful_predictions,
    get_total_predictions,
)
from ui import render_table


def get_scalar(result, column_name, fallback="—"):
    if result["ok"] and not result["data"].empty:
        value = result["data"].iloc[0][column_name]
        return fallback if value is None else value

    return fallback


def render_monitoring_card(title, value, caption, icon):
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


def render_monitoring_page():
    st.markdown(
        """
<div class="page-section">
    <div class="page-eyebrow">Monitoring</div>
    <h2 class="page-title">Monitoring</h2>
    <p class="page-description">
        Analyze prediction reliability, latency, status distribution, and recent system activity.
    </p>
</div>
""",
        unsafe_allow_html=True,
    )

    total_predictions = get_total_predictions()
    successful_predictions = get_successful_predictions()
    failed_predictions = get_failed_predictions()
    latency_stats = get_latency_stats()
    prediction_status = get_prediction_status_distribution()
    prediction_trend = get_prediction_trend()

    total = get_scalar(total_predictions, "total_predictions")
    success = get_scalar(successful_predictions, "successful_predictions")
    failed = get_scalar(failed_predictions, "failed_predictions")
    avg_latency = get_scalar(latency_stats, "avg_latency")

    if avg_latency != "—":
        avg_latency = f"{round(float(avg_latency), 2)} ms"

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_monitoring_card("Total Predictions", total, "All inference requests", "⌁")

    with col2:
        render_monitoring_card("Successful", success, "Healthy predictions", "✓")

    with col3:
        render_monitoring_card("Failed", failed, "Failed requests", "×")

    with col4:
        render_monitoring_card("Avg Latency", avg_latency, "Mean response time", "↯")

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    left_col, right_col = st.columns([0.4, 0.6])

    with left_col:
        st.markdown(
            """
<div class="dashboard-card table-card">
    <div class="card-title">Prediction Status Distribution</div>
    <div class="card-subtitle">
        Count of predictions grouped by status.
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

        render_table(
            prediction_status,
            "",
            "No prediction status data found.",
        )

    with right_col:
        st.markdown(
            """
<div class="dashboard-card table-card">
    <div class="card-title">Predictions Over Time</div>
    <div class="card-subtitle">
        Daily prediction volume trend.
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

        if prediction_trend["ok"]:
            trend_df = prediction_trend["data"]

            if trend_df.empty:
                st.info("No prediction trend data found.")

            elif len(trend_df) < 2:
                st.info("Not enough data points to render a trend chart yet.")
                st.dataframe(trend_df, width="stretch", hide_index=True)

            else:
                trend_df = trend_df.copy()
                trend_df["day"] = pd.to_datetime(trend_df["day"])
                trend_df = trend_df.sort_values("day")
                trend_df = trend_df.set_index("day")

                st.line_chart(trend_df, width="stretch")

        else:
            st.error(prediction_trend["error"])

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    st.markdown(
        """
<div class="dashboard-card table-card">
    <div class="card-title">Recent Prediction Logs</div>
    <div class="card-subtitle">
        Latest prediction events captured by the monitoring system.
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