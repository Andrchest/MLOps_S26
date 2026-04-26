from datetime import datetime

import pandas as pd
import streamlit as st

from db import check_db_health
from repository import (
    get_datasets,
    get_deployments,
    get_failed_predictions,
    get_job_status_counts,
    get_jobs,
    get_latency_stats,
    get_models,
    get_prediction_status_distribution,
    get_prediction_trend,
    get_recent_prediction_logs,
    get_service_health,
    get_successful_predictions,
    get_total_jobs,
    get_total_models,
    get_total_predictions,
)
from ui import render_health_table, render_metric, render_table

st.set_page_config(page_title="Monitoring Dashboard", page_icon="📊", layout="wide")

st.title("Monitoring Dashboard")
st.caption("Read-only dashboard for jobs, models, and overall system visibility.")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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

    jobs_result = get_jobs()

    render_table(
        jobs_result,
        "Jobs",
        "No jobs found yet. Start a training job to populate this table.",
    )

    if jobs_result["ok"] and not jobs_result["data"].empty:
        df = jobs_result["data"]

        selected_job_id = st.selectbox(
            "Select Job ID to view details",
            df["job_id"].tolist(),
        )

        selected_job = df[df["job_id"] == selected_job_id].iloc[0]

        st.markdown("### Job Details")

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Job ID:** {selected_job['job_id']}")
            st.write(f"**Dataset Name:** {selected_job['dataset_name']}")

        with col2:
            st.write(f"**Dataset ID:** {selected_job['dataset_id']}")
            st.write(f"**Status:** {selected_job['status']}")

elif page == "Datasets":
    st.header("Datasets")
    render_table(
        get_datasets(),
        "Datasets",
        "No datasets found yet. Upload a dataset using the orchestrator API.",
    )

elif page == "Models":
    st.header("Models")
    render_table(
        get_models(),
        "Trained Models",
        "No trained models found yet. Complete a training job to populate this table.",
    )

elif page == "Deployments":
    st.header("Deployments")
    render_table(
        get_deployments(),
        "Deployments",
        "No deployments found yet. Train and deploy a model to populate this table.",
    )

elif page == "Monitoring":
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

elif page == "System Health":
    st.header("System Health")
    st.caption("Live status from service health endpoints.")
    render_health_table(get_service_health())