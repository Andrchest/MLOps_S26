import streamlit as st

from repository import get_datasets
from ui import render_table


def render_datasets_page():
    st.header("Datasets")
    render_table(
        get_datasets(),
        "Datasets",
        "No datasets found yet. Upload a dataset using the orchestrator API.",
    )