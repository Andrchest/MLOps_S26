import streamlit as st

from repository import get_deployments
from ui import render_table


def render_deployments_page():
    st.header("Deployments")
    render_table(
        get_deployments(),
        "Deployments",
        "No deployments found yet. Train and deploy a model to populate this table.",
    )