from datetime import datetime

import streamlit as st

from dashboard_pages.datasets import render_datasets_page
from dashboard_pages.deployments import render_deployments_page
from dashboard_pages.inference import render_inference_page
from dashboard_pages.jobs import render_jobs_page
from dashboard_pages.models import render_models_page
from dashboard_pages.monitoring import render_monitoring_page
from dashboard_pages.overview import render_overview_page
from dashboard_pages.system_health import render_system_health_page
from db import check_db_health

st.set_page_config(page_title="Monitoring Dashboard", page_icon="📊", layout="wide")


# ----------------------
# Mock Authentication
# ----------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def login():
    st.title("Monitoring Dashboard")
    st.caption("Sign in to access the MLOps monitoring dashboard.")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "admin123":
            st.session_state.authenticated = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Invalid credentials")


if not st.session_state.authenticated:
    login()
    st.stop()


# ----------------------
# Dashboard Shell
# ----------------------
st.title("Monitoring Dashboard")
st.caption("Read-only dashboard for jobs, models, and overall system visibility.")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.sidebar.title("Navigation")

section = st.sidebar.radio(
    "Sections",
    ["Overview", "Operations", "Monitoring", "System"],
)

if section == "Overview":
    page = "System Overview"

elif section == "Operations":
    page = st.sidebar.radio(
        "Operations",
        ["Jobs", "Datasets", "Models", "Deployments"],
    )

elif section == "Monitoring":
    page = st.sidebar.radio(
        "Monitoring",
        ["Inference", "Monitoring"],
    )

else:
    page = "System Health"

st.sidebar.markdown("---")
st.sidebar.markdown(f"**User:** {st.session_state.get('username', 'admin')}")

if st.sidebar.button("Refresh"):
    st.rerun()

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()


# ----------------------
# DB Health Check
# ----------------------
db_ok, db_error = check_db_health()

if not db_ok:
    st.error(f"Database unavailable: {db_error}")
    st.info("The dashboard is running, but DB-backed data cannot be loaded.")
    st.stop()


# ----------------------
# Router
# ----------------------
if page == "System Overview":
    render_overview_page()

elif page == "Jobs":
    render_jobs_page()

elif page == "Datasets":
    render_datasets_page()

elif page == "Models":
    render_models_page()

elif page == "Deployments":
    render_deployments_page()

elif page == "Inference":
    render_inference_page()

elif page == "Monitoring":
    render_monitoring_page()

elif page == "System Health":
    render_system_health_page()