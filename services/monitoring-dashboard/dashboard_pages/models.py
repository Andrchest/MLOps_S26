import streamlit as st

from repository import get_models
from ui import render_metric, render_table


def render_models_page():
    st.header("Models")
    st.caption("Explore trained models, versions, metrics, and parameters.")

    models_result = get_models()

    if not models_result["ok"] or models_result["data"].empty:
        render_table(
            models_result,
            "Trained Models",
            "No trained models found yet. Complete a training job to populate this table.",
        )
        return

    df = models_result["data"]

    model_filter = st.text_input("Search Model Name")

    filtered_df = df.copy()

    if model_filter:
        filtered_df = filtered_df[
            filtered_df["model_name"].str.contains(
                model_filter,
                case=False,
                na=False,
            )
        ]

    filtered_result = {"ok": True, "data": filtered_df, "error": None}

    render_table(
        filtered_result,
        "Trained Models",
        "No models match the selected search.",
    )

    if filtered_df.empty:
        return

    st.divider()

    selected_model_index = st.selectbox(
        "Select Model",
        filtered_df.index.tolist(),
        format_func=lambda index: (
            f"{filtered_df.loc[index, 'model_name']} "
            f"(v{filtered_df.loc[index, 'model_version']})"
        ),
    )

    selected_model = filtered_df.loc[selected_model_index]

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