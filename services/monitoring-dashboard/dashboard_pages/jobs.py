import streamlit as st

from repository import get_jobs
from ui import render_metric, render_status_badge, render_table


def render_jobs_page():
    st.header("Jobs")
    st.caption("Track training jobs, their dataset associations, and execution status.")

    jobs_result = get_jobs()

    if not jobs_result["ok"]:
        render_table(
            jobs_result,
            "Jobs",
            "No jobs found yet. Start a training job to populate this table.",
        )
        return

    df = jobs_result["data"]

    if df.empty:
        render_table(
            jobs_result,
            "Jobs",
            "No jobs found yet. Start a training job to populate this table.",
        )
        return

    status_options = ["All"] + sorted(df["status"].dropna().unique().tolist())

    status_filter = st.selectbox(
        "Filter by Status",
        status_options,
    )

    filtered_df = df.copy()

    if status_filter != "All":
        filtered_df = filtered_df[filtered_df["status"] == status_filter]

    filtered_result = {
        "ok": True,
        "data": filtered_df,
        "error": None,
    }

    render_table(
        filtered_result,
        "Jobs",
        "No jobs match the selected filter.",
    )

    if filtered_df.empty:
        return

    st.divider()

    selected_job_id = st.selectbox(
        "Select Job",
        filtered_df["job_id"].tolist(),
        format_func=lambda job_id: f"Job #{job_id}",
    )

    selected_job = filtered_df[filtered_df["job_id"] == selected_job_id].iloc[0]

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