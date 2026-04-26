import streamlit as st

from repository import get_service_health
from ui import render_health_table


def render_system_health_page():
    st.header("System Health")
    st.caption("Live status from service health endpoints.")
    render_health_table(get_service_health())