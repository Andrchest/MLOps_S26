import streamlit as st

from repository import get_models
from ui import render_table


def render_model_card(title, value, caption, icon):
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
    <div class="empty-state-icon">◇</div>
    <div class="empty-state-title">No trained models found</div>
    <div class="empty-state-text">
        Complete a training job to populate this page.
    </div>
</div>
"""
    )


def render_models_page():
    st.markdown(
        """
<div class="page-section">
    <div class="page-eyebrow">Operations</div>
    <h2 class="page-title">Models</h2>
    <p class="page-description">
        Explore trained models, versions, metrics, parameters, and stored model paths.
    </p>
</div>
""",
        unsafe_allow_html=True,
    )

    models_result = get_models()

    if not models_result["ok"]:
        render_table(
            models_result,
            "Trained Models",
            "Unable to load trained models.",
        )
        return

    if models_result["data"].empty:
        render_empty_state()
        return

    df = models_result["data"].copy()

    total_models = len(df)
    unique_model_names = df["model_name"].nunique() if "model_name" in df.columns else 0
    unique_versions = df["model_version"].nunique() if "model_version" in df.columns else 0
    linked_jobs = df["job_id"].nunique() if "job_id" in df.columns else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_model_card("Total Models", total_models, "All trained model records", "◇")

    with col2:
        render_model_card("Model Names", unique_model_names, "Unique model families", "▦")

    with col3:
        render_model_card("Versions", unique_versions, "Tracked model versions", "↥")

    with col4:
        render_model_card("Linked Jobs", linked_jobs, "Training jobs connected", "☷")

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    search_col, export_col = st.columns([0.75, 0.25])

    with search_col:
        model_filter = st.text_input(
            "Search Model Name",
            placeholder="Search by model name...",
        )

    filtered_df = df.copy()

    if model_filter:
        filtered_df = filtered_df[
            filtered_df["model_name"].str.contains(
                model_filter,
                case=False,
                na=False,
            )
        ]

    with export_col:
        csv = filtered_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="models.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown(
        """
<div class="dashboard-card table-card">
    <div class="card-title">Trained Models</div>
    <div class="card-subtitle">
        Browse registered models and inspect their versions, metrics, and parameters.
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    render_table(
        {"ok": True, "data": filtered_df, "error": None},
        "",
        "No models match the selected search.",
    )

    if filtered_df.empty:
        return

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    selected_model_index = st.selectbox(
        "Select Model",
        filtered_df.index.tolist(),
        format_func=lambda index: (
            f"{filtered_df.loc[index, 'model_name']} "
            f"(v{filtered_df.loc[index, 'model_version']})"
        ),
    )

    selected_model = filtered_df.loc[selected_model_index]

    st.html(
        f"""
<div class="dashboard-card detail-card">
    <div class="detail-header">
        <div>
            <div class="card-title">{selected_model["model_name"]}</div>
            <div class="card-subtitle">Selected model details and training context.</div>
        </div>
        <div class="status-pill">
            v{selected_model["model_version"]}
        </div>
    </div>

    <div class="detail-grid">
        <div class="detail-item">
            <div class="detail-label">Model Name</div>
            <div class="detail-value">{selected_model["model_name"]}</div>
        </div>

        <div class="detail-item">
            <div class="detail-label">Version</div>
            <div class="detail-value">{selected_model["model_version"]}</div>
        </div>

        <div class="detail-item">
            <div class="detail-label">Job ID</div>
            <div class="detail-value">{selected_model["job_id"]}</div>
        </div>
    </div>

    <div class="path-card">
        <div class="detail-label">Model Path</div>
        <div class="path-value">{selected_model["model_path"]}</div>
    </div>
</div>
"""
    )

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    metric_col, param_col = st.columns(2)

    with metric_col:
        st.markdown(
            """
<div class="dashboard-card table-card">
    <div class="card-title">Metrics</div>
    <div class="card-subtitle">Evaluation metrics saved for this model.</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.json(selected_model["metrics"])

    with param_col:
        st.markdown(
            """
<div class="dashboard-card table-card">
    <div class="card-title">Parameters</div>
    <div class="card-subtitle">Training parameters used for this model.</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.json(selected_model["parameters"])