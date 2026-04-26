import streamlit as st

from repository import (
    get_failed_predictions,
    get_latency_stats,
    get_recent_prediction_logs,
    get_successful_predictions,
    get_total_predictions,
)
from ui import render_metric, render_status_badge, render_table


def render_inference_page():
    st.header("Inference")

    total_predictions = get_total_predictions()
    successful_predictions = get_successful_predictions()
    failed_predictions = get_failed_predictions()
    latency_stats = get_latency_stats()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if total_predictions["ok"] and not total_predictions["data"].empty:
            render_metric(
                "Total",
                int(total_predictions["data"].iloc[0]["total_predictions"]),
            )
        else:
            st.warning("N/A")

    with col2:
        if successful_predictions["ok"] and not successful_predictions["data"].empty:
            render_metric(
                "Success",
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
                round(float(avg_latency), 2) if avg_latency else "N/A",
            )
        else:
            st.warning("N/A")

    st.divider()

    logs_result = get_recent_prediction_logs()

    render_table(
        logs_result,
        "Recent Predictions",
        "No predictions found.",
    )

    if logs_result["ok"] and not logs_result["data"].empty:
        df = logs_result["data"]

        selected_request = st.selectbox(
            "Select Prediction",
            df["request_id"].tolist(),
        )

        selected = df[df["request_id"] == selected_request].iloc[0]

        st.markdown("### Prediction Details")

        col1, col2 = st.columns(2)

        with col1:
            render_metric("Request ID", selected["request_id"])
            render_metric("Model", selected["model_name"])

        with col2:
            render_metric("Version", selected["model_version"])
            st.metric("Status", render_status_badge(selected["status"]))

        st.markdown("#### Latency")
        st.info(f"{selected['latency_ms']} ms")