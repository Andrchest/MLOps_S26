import streamlit as st

from repository import get_models
from ui import render_metric, render_table


def render_models_page():
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