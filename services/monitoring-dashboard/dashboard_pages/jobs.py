import streamlit as st

from repository import get_jobs
from ui import render_metric, render_status_badge, render_table


def render_jobs_page():
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