import base64
from pathlib import Path

import streamlit as st


APP_LOGO_PATH = "../assets/innopolis-logo.svg"


def get_logo_base64(path):
    logo_path = Path(path)

    if not logo_path.exists():
        return None

    return base64.b64encode(logo_path.read_bytes()).decode()


def render_login():
    logo_base64 = get_logo_base64(APP_LOGO_PATH)

    if logo_base64:
        logo_html = f'<img class="login-logo-img" src="data:image/svg+xml;base64,{logo_base64}" />'
    else:
        logo_html = '<div class="login-logo-fallback">IU</div>'

    left_col, center_col, right_col = st.columns([1, 1.15, 1])

    with center_col:
        st.markdown(
            f"""
            <div class="login-panel">
                {logo_html}
                <h1>Welcome back</h1>
                <p>Sign in to access the MLOps Monitoring Center.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter password",
        )

        login_clicked = st.button(
            "Login",
            use_container_width=True,
            type="primary",
        )

        st.markdown(
            """
            <div class="login-footer">
                Read-only dashboard • v2.0
            </div>
            """,
            unsafe_allow_html=True,
        )

    return username, password, login_clicked