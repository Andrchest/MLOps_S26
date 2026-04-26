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
from ui import render_metric, render_table


def render_monitoring_page():
    st.header("Monitoring")

    total_predictions = get_total_predictions()
    successful_predictions = get_successful_predictions()
    failed_predictions = get_failed_predictions()
    latency_stats = get_latency_stats()
    prediction_status = get_prediction_status_distribution()
    prediction_trend = get_prediction_trend()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if total_predictions["ok"] and not total_predictions["data"].empty:
            render_metric(
                "Total Predictions",
                int(total_predictions["data"].iloc[0]["total_predictions"]),
            )
        else:
            st.warning("N/A")

    with col2:
        if successful_predictions["ok"] and not successful_predictions["data"].empty:
            render_metric(
                "Successful",
                int(successful_predictions["data"].iloc[0]["successful_predictions"]),
            )
        else:
            st.warning("N/A")

    with col3:
        if failed_predictions["ok"] and not failed_predictions["data"].empty:
            render_metric(
                "Failed",
                int(failed_predictions["data"].iloc[0]["failed_predictions"]),
            )
        else:
            st.warning("N/A")

    with col4:
        if latency_stats["ok"] and not latency_stats["data"].empty:
            avg_latency = latency_stats["data"].iloc[0]["avg_latency"]
            render_metric(
                "Avg Latency (ms)",
                round(float(avg_latency), 2) if avg_latency is not None else "N/A",
            )
        else:
            st.warning("N/A")

    render_table(
        prediction_status,
        "Prediction Status Distribution",
        "No prediction status data found.",
    )

    st.subheader("Predictions Over Time")

    if prediction_trend["ok"]:
        trend_df = prediction_trend["data"]

        if trend_df.empty:
            st.info("No prediction trend data found.")

        elif len(trend_df) < 2:
            st.info("Not enough data points to render a trend chart yet.")
            st.dataframe(trend_df, use_container_width=True, hide_index=True)

        else:
            trend_df["day"] = pd.to_datetime(trend_df["day"])
            trend_df = trend_df.sort_values("day")
            trend_df = trend_df.set_index("day")

            st.line_chart(trend_df, use_container_width=True)

    else:
        st.error(prediction_trend["error"])

    render_table(
        get_recent_prediction_logs(),
        "Recent Prediction Logs",
        "No prediction logs available.",
    )