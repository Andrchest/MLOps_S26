import base64
from pathlib import Path

import streamlit as st


APP_LOGO_PATH = "../assets/innopolis-logo.svg"
APP_NAME = "MLOps"
APP_SUBTITLE = "Monitoring Center"


NAV_GROUPS = [
    {
        "title": "Overview",
        "items": [
            {"key": "System Overview", "label": "Overview", "icon": "▦"},
        ],
    },
    {
        "title": "Operations",
        "items": [
            {"key": "Jobs", "label": "Jobs", "icon": "☷"},
            {"key": "Datasets", "label": "Datasets", "icon": "▤"},
            {"key": "Models", "label": "Models", "icon": "◇"},
            {"key": "Deployments", "label": "Deployments", "icon": "↥"},
        ],
    },
    {
        "title": "Monitoring",
        "items": [
            {"key": "Inference", "label": "Inference", "icon": "⌁"},
            {"key": "Monitoring", "label": "Monitoring", "icon": "⌇"},
        ],
    },
    {
        "title": "System",
        "items": [
            {"key": "System Health", "label": "System Health", "icon": "◌"},
        ],
    },
]


def get_logo_base64(path):
    logo_path = Path(path)

    if not logo_path.exists():
        return None

    return base64.b64encode(logo_path.read_bytes()).decode()


def init_navigation_state():
    if "current_page" not in st.session_state:
        st.session_state.current_page = "System Overview"


def render_sidebar():
    init_navigation_state()
    logo_base64 = get_logo_base64(APP_LOGO_PATH)

    with st.sidebar:
        if logo_base64:
            logo_html = f'<img class="logo-img" src="data:image/svg+xml;base64,{logo_base64}" />'
        else:
            logo_html = '<div class="logo-fallback">IU</div>'

        st.markdown(
            f"""
            <div class="sidebar-logo">
                {logo_html}
                <div>
                    <div class="logo-title">{APP_NAME}</div>
                    <div class="logo-subtitle">{APP_SUBTITLE}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for group in NAV_GROUPS:
            st.markdown(
                f'<div class="nav-group">{group["title"]}</div>',
                unsafe_allow_html=True,
            )

            for item in group["items"]:
                is_active = item["key"] == st.session_state.current_page

                if st.button(
                    f'{item["icon"]}   {item["label"]}',
                    key=f"nav_{item['key']}",
                    width="stretch",
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state.current_page = item["key"]
                    st.rerun()

        username = st.session_state.get("username", "admin")

        st.markdown(
            f"""
            <div class="account-card">
                <div class="avatar">{username[:1].upper()}</div>
                <div>
                    <div class="account-name">{username}</div>
                    <div class="account-role">Dashboard Admin</div>
                </div>
            </div>

            <div class="sidebar-footer">
                <div>v2.0</div>
                <div>Read-only monitoring dashboard</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return st.session_state.current_page