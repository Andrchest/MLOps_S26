import streamlit as st

from repository import get_jobs
from ui import render_status_badge, render_table


def render_job_card(title, value, caption, icon):
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
    st.markdown(
        """
<div class="dashboard-card empty-state-card">
    <div class="empty-state-icon">☷</div>
    <div class="empty-state-title">No jobs found</div>
    <div class="empty-state-text">
        Start a training job to populate this page.
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_jobs_page():
    st.markdown(
        """
<div class="page-section">
    <div class="page-eyebrow">Operations</div>
    <h2 class="page-title">Jobs</h2>
    <p class="page-description">
        Track training jobs, dataset associations, and execution status.
    </p>
</div>
""",
        unsafe_allow_html=True,
    )

    jobs_result = get_jobs()

    if not jobs_result["ok"]:
        render_table(
            jobs_result,
            "Jobs",
            "Unable to load jobs.",
        )
        return

    if jobs_result["data"].empty:
        render_empty_state()
        return

    df = jobs_result["data"].copy()
    df["status"] = df["status"].fillna("unknown")

    total_jobs = len(df)
    succeeded_jobs = len(df[df["status"].str.lower() == "succeeded"])
    failed_jobs = len(df[df["status"].str.lower() == "failed"])
    running_jobs = len(df[df["status"].str.lower() == "running"])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_job_card("Total Jobs", total_jobs, "All recorded jobs", "☷")

    with col2:
        render_job_card("Succeeded", succeeded_jobs, "Completed successfully", "✓")

    with col3:
        render_job_card("Running", running_jobs, "Currently in progress", "↻")

    with col4:
        render_job_card("Failed", failed_jobs, "Jobs requiring attention", "×")

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    filter_col, export_col = st.columns([0.75, 0.25])

    with filter_col:
        status_options = ["All"] + sorted(df["status"].dropna().unique().tolist())
        status_filter = st.selectbox("Filter by Status", status_options)

    filtered_df = df.copy()

    if status_filter != "All":
        filtered_df = filtered_df[filtered_df["status"] == status_filter]

    with export_col:
        csv = filtered_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="jobs.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown(
        """
<div class="dashboard-card table-card">
    <div class="card-title">Jobs Table</div>
    <div class="card-subtitle">
        Browse job records and inspect their current status.
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    render_table(
        {"ok": True, "data": filtered_df, "error": None},
        "",
        "No jobs match the selected filter.",
    )

    if filtered_df.empty:
        return

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    selected_job_id = st.selectbox(
        "Select Job",
        filtered_df["job_id"].tolist(),
        format_func=lambda job_id: f"Job #{job_id}",
    )

    selected_job = filtered_df[filtered_df["job_id"] == selected_job_id].iloc[0]

    st.html(
        f"""
        <div class="dashboard-card detail-card">
            <div class="detail-header">
                <div>
                    <div class="card-title">Job #{selected_job["job_id"]}</div>
                    <div class="card-subtitle">Selected job details and dataset context.</div>
                </div>
                <div class="status-pill">
                    {render_status_badge(selected_job["status"])}
                </div>
            </div>

            <div class="detail-grid">
                <div class="detail-item">
                    <div class="detail-label">Job ID</div>
                    <div class="detail-value">{selected_job["job_id"]}</div>
                </div>

                <div class="detail-item">
                    <div class="detail-label">Dataset ID</div>
                    <div class="detail-value">{selected_job["dataset_id"]}</div>
                </div>

                <div class="detail-item">
                    <div class="detail-label">Dataset Name</div>
                    <div class="detail-value">{selected_job["dataset_name"]}</div>
                </div>
            </div>
        </div>
        """
    )