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
from ui import render_health_table, render_metric, render_status_badge, render_table

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login():
    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "admin123":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid credentials")

if not st.session_state.authenticated:
    login()
    st.stop()

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
        "Inference",
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

        st.divider()

        selected_job_id = st.selectbox(
            "Select Job",
            df["job_id"].tolist(),
            format_func=lambda job_id: f"Job #{job_id}",
        )

        selected_job = df[df["job_id"] == selected_job_id].iloc[0]

        st.markdown("### Job Details")

        col1, col2, col3 = st.columns(3)

        with col1:
            render_metric("Job ID", selected_job["job_id"])

        with col2:
            render_metric("Dataset ID", selected_job["dataset_id"])

        with col3:
            st.metric("Status", render_status_badge(selected_job["status"]))

        st.markdown("#### Dataset")
        st.info(selected_job["dataset_name"])

elif page == "Models":
    st.header("Models")

    models_result = get_models()

    render_table(
        models_result,
        "Trained Models",
        "No trained models found yet. Complete a training job to populate this table.",
    )

    if models_result["ok"] and not models_result["data"].empty:
        df = models_result["data"]

        st.divider()

        selected_model_index = st.selectbox(
            "Select Model",
            df.index.tolist(),
            format_func=lambda index: (
                f"{df.loc[index, 'model_name']} "
                f"(v{df.loc[index, 'model_version']})"
            ),
        )

        selected_model = df.loc[selected_model_index]

        st.markdown("### Model Details")

        col1, col2, col3 = st.columns(3)

        with col1:
            render_metric("Model Name", selected_model["model_name"])

        with col2:
            render_metric("Version", selected_model["model_version"])

        with col3:
            render_metric("Job ID", selected_model["job_id"])

        st.markdown("#### Model Path")
        st.code(selected_model["model_path"])

        with st.expander("Metrics", expanded=True):
            st.json(selected_model["metrics"])

        with st.expander("Parameters"):
            st.json(selected_model["parameters"])

elif page == "Deployments":
    st.header("Deployments")
    render_table(
        get_deployments(),
        "Deployments",
        "No deployments found yet. Train and deploy a model to populate this table.",
    )

elif page == "Inference":
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