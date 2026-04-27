import streamlit as st

from repository import get_service_health
from ui import render_health_table


def render_health_card(title, value, caption, icon):
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


def render_status_banner(status_type, title, message):
    st.markdown(
        f"""
<div class="dashboard-card status-card status-{status_type}">
    <div>
        <div class="status-title">{title}</div>
        <div class="status-message">{message}</div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_system_health_page():
    st.markdown(
        """
<div class="page-section">
    <div class="page-eyebrow">System</div>
    <h2 class="page-title">System Health</h2>
    <p class="page-description">
        Real-time visibility into service availability and system reliability.
    </p>
</div>
""",
        unsafe_allow_html=True,
    )

    health_result = get_service_health()

    if not health_result["ok"]:
        render_status_banner(
            "down",
            "Health data unavailable",
            health_result["error"],
        )
        return

    df = health_result["data"]

    if df.empty:
        render_status_banner(
            "unknown",
            "No health data",
            "No services are currently reporting health status.",
        )
        return

    statuses = df["status"].str.lower().tolist()

    total_services = len(df)
    healthy = len([s for s in statuses if s == "healthy"])
    degraded = len([s for s in statuses if s == "degraded"])
    down = len([s for s in statuses if s == "down"])

    # ----------------------
    # Status Banner
    # ----------------------
    if down > 0:
        render_status_banner(
            "down",
            "System issues detected",
            "One or more services are currently down and require attention.",
        )
    elif degraded > 0:
        render_status_banner(
            "degraded",
            "System degraded",
            "Some services are running with degraded performance.",
        )
    else:
        render_status_banner(
            "healthy",
            "All systems operational",
            "All monitored services are healthy and functioning normally.",
        )

    # ----------------------
    # KPI Cards
    # ----------------------
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_health_card("Total Services", total_services, "All tracked services", "◌")

    with col2:
        render_health_card("Healthy", healthy, "Operating normally", "✓")

    with col3:
        render_health_card("Degraded", degraded, "Partial issues", "⚠")

    with col4:
        render_health_card("Down", down, "Critical failures", "×")

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    # ----------------------
    # Table
    # ----------------------
    st.markdown(
        """
<div class="dashboard-card table-card">
    <div class="card-title">Service Health</div>
    <div class="card-subtitle">
        Live status of all monitored services.
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    render_health_table(health_result)