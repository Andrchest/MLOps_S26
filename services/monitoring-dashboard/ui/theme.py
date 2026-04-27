import streamlit as st

PRIMARY_COLOR = "#40BA21"


def apply_global_styles():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        :root {{
            --primary: {PRIMARY_COLOR};
            --primary-hover: #379F1C;
            --primary-active: #2E8517;

            --app-bg: #071009;
            --surface: rgba(255,255,255,0.055);
            --surface-soft: rgba(255,255,255,0.03);
            --surface-hover: rgba(255,255,255,0.06);

            --primary-soft: rgba(64,186,33,0.12);
            --primary-soft-2: rgba(64,186,33,0.08);
            --primary-border: rgba(64,186,33,0.36);
            --primary-glow: rgba(64,186,33,0.22);

            --sidebar-bg: #071009;
            --sidebar-bg-2: #08100A;
            --sidebar-border: rgba(64,186,33,0.12);

            --text-main: #F4FFF4;
            --text-muted: #9FB79F;
            --text-soft: #BFD6BF;

            --card-bg: linear-gradient(180deg, rgba(255,255,255,0.055), rgba(255,255,255,0.025));
            --card-border: rgba(64,186,33,0.14);
            --shadow: 0 18px 50px rgba(0,0,0,0.18);

            --input-bg: rgba(255,255,255,0.055);
            --input-border: rgba(255,255,255,0.08);
        }}

        @media (prefers-color-scheme: light) {{
            :root {{
                --app-bg: #F7FAF7;
                --surface: #FFFFFF;
                --surface-soft: #F2F7F2;
                --surface-hover: #EEF7EE;

                --primary-soft: rgba(64,186,33,0.10);
                --primary-soft-2: rgba(64,186,33,0.06);
                --primary-border: rgba(64,186,33,0.28);
                --primary-glow: rgba(64,186,33,0.14);

                --sidebar-bg: #F4FAF3;
                --sidebar-bg-2: #EAF5E8;
                --sidebar-border: rgba(64,186,33,0.16);

                --text-main: #102015;
                --text-muted: #5F765F;
                --text-soft: #385238;

                --card-bg: linear-gradient(180deg, #FFFFFF, #F8FCF7);
                --card-border: rgba(64,186,33,0.18);
                --shadow: 0 18px 50px rgba(16,32,21,0.08);

                --input-bg: #FFFFFF;
                --input-border: rgba(16,32,21,0.12);
            }}
        }}

        /* Global text */
        h1, h2, h3, h4, h5, h6, p, span, label {{
            color: var(--text-main);
        }}

        /* Global Buttons */
        .stButton > button {{
            min-height: 48px;
            border-radius: 12px;
            font-weight: 800;
            transition: all 0.16s ease;
        }}

        .stButton > button[kind="primary"] {{
            background: var(--primary);
            border: 1px solid var(--primary);
            color: #071009;
        }}

        .stButton > button[kind="primary"]:hover {{
            background: var(--primary-hover);
            border-color: var(--primary-hover);
            color: #071009;
            transform: translateY(-1px);
        }}

        /* Inputs */
        .stTextInput {{
            margin-bottom: 16px;
        }}

        .stTextInput input {{
            min-height: 48px;
            border-radius: 12px;
            border: 1px solid var(--input-border);
            background: var(--input-bg);
            color: var(--text-main);
        }}

        .stTextInput input:focus {{
            border-color: var(--primary-border);
            box-shadow: 0 0 0 3px var(--primary-soft);
        }}

        .stTextInput input::placeholder {{
            color: var(--text-muted);
        }}

        /* Login Page */
        .login-panel {{
            width: 100%;
            box-sizing: border-box;
            margin: 48px 0 32px 0;
            padding: 40px;
            border-radius: 24px;
            background:
                radial-gradient(circle at top left, var(--primary-soft), transparent 44%),
                var(--card-bg);
            border: 1px solid var(--card-border);
            box-shadow: var(--shadow);
        }}

        .login-logo-img,
        .login-logo-fallback {{
            width: 56px;
            height: 56px;
            margin-bottom: 24px;
            border-radius: 16px;
            object-fit: contain;
            background: linear-gradient(135deg, var(--primary), #65D84C);
            box-shadow: 0 16px 36px var(--primary-glow);
        }}

        .login-logo-fallback {{
            color: #071009;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
            font-size: 18px;
        }}

        .login-panel h1 {{
            margin: 0 0 16px 0;
            color: var(--text-main);
            font-size: 34px;
            font-weight: 900;
            line-height: 1.1;
        }}

        .login-panel p {{
            margin: 0;
            color: var(--text-muted);
            font-size: 14px;
        }}

        .login-footer {{
            margin-top: 40px;
            color: var(--text-muted);
            font-size: 12px;
            text-align: center;
        }}

        /* Sidebar */
        [data-testid="stSidebar"] {{
            background:
                radial-gradient(circle at top left, var(--primary-soft), transparent 34%),
                linear-gradient(180deg, var(--sidebar-bg) 0%, var(--sidebar-bg-2) 100%);
            border-right: 1px solid var(--sidebar-border);
        }}

        [data-testid="stSidebar"] > div:first-child {{
            padding: 16px 16px 20px 16px;
        }}

        .sidebar-logo {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding-bottom: 20px;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--sidebar-border);
        }}

        .logo-img,
        .logo-fallback {{
            width: 48px;
            height: 48px;
            border-radius: 14px;
            object-fit: contain;
            background: var(--primary);
            box-shadow: 0 12px 28px var(--primary-glow);
        }}

        .logo-fallback {{
            color: #071009;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
        }}

        .logo-title {{
            color: var(--text-main);
            font-size: 16px;
            font-weight: 800;
            line-height: 1.1;
        }}

        .logo-subtitle {{
            color: var(--text-muted);
            font-size: 12px;
            margin-top: 4px;
        }}

        .nav-group {{
            color: var(--text-muted);
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            margin: 20px 0 8px;
        }}

        [data-testid="stSidebar"] .stButton > button {{
            min-height: 44px;
            height: 44px;
            display: flex;
            align-items: center;
            justify-content: flex-start;
            text-align: left;
            padding: 0 14px;
            margin: 0 0 4px 0;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 700;
            transition: background 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
        }}

        [data-testid="stSidebar"] .stButton > button[kind="secondary"] {{
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-soft);
        }}

        [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {{
            background: var(--surface-hover);
            border-color: var(--sidebar-border);
            color: var(--text-main);
            transform: translateX(2px);
        }}

        [data-testid="stSidebar"] .stButton > button[kind="primary"],
        [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {{
            background: linear-gradient(90deg, var(--primary-soft), var(--primary-soft-2));
            border: 1px solid var(--primary-border);
            color: var(--text-main);
            box-shadow:
                inset 3px 0 0 var(--primary),
                0 12px 26px var(--primary-glow);
            transform: none;
        }}

        .account-card {{
            margin-top: 28px;
            padding: 16px;
            border-radius: 18px;
            background: linear-gradient(180deg, var(--primary-soft), var(--primary-soft-2));
            border: 1px solid var(--primary-border);
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .avatar {{
            width: 44px;
            height: 44px;
            border-radius: 14px;
            background: var(--primary-soft);
            color: var(--primary);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 900;
        }}

        .account-name {{
            color: var(--text-main);
            font-weight: 800;
            font-size: 14px;
        }}

        .account-role {{
            color: var(--text-muted);
            font-size: 12px;
            margin-top: 4px;
        }}

        .sidebar-footer {{
            color: var(--text-muted);
            font-size: 11px;
            margin-top: 24px;
            line-height: 1.6;
        }}

        /* Dashboard Pages */
        .page-section {{
            margin: 24px 0 24px 0;
        }}

        .page-eyebrow {{
            color: var(--primary);
            font-size: 12px;
            font-weight: 900;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}

        .page-title {{
            color: var(--text-main);
            font-size: 34px;
            font-weight: 900;
            line-height: 1.1;
            margin: 0 0 12px 0;
        }}

        .page-description {{
            color: var(--text-muted);
            font-size: 15px;
            margin: 0;
        }}

        .dashboard-card {{
            border-radius: 20px;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            box-shadow: var(--shadow);
        }}

        .stat-card {{
            min-height: 132px;
            padding: 24px;
            border-top: 3px solid var(--primary);
        }}

        .stat-icon {{
            color: var(--primary);
            font-size: 24px;
            margin-bottom: 12px;
        }}

        .stat-value {{
            color: var(--text-main);
            font-size: 34px;
            font-weight: 900;
            line-height: 1;
            margin-bottom: 8px;
        }}

        .stat-title {{
            color: var(--text-main);
            font-size: 14px;
            font-weight: 800;
            margin-bottom: 4px;
        }}

        .stat-caption {{
            color: var(--text-muted);
            font-size: 12px;
        }}

        .status-card {{
            padding: 20px 24px;
            margin-bottom: 24px;
        }}

        .status-card.status-healthy {{
            border-color: var(--primary-border);
            background:
                radial-gradient(circle at top left, var(--primary-soft), transparent 38%),
                var(--card-bg);
        }}

        .status-card.status-degraded {{
            border-color: rgba(255,176,32,0.45);
        }}

        .status-card.status-down {{
            border-color: rgba(255,82,82,0.45);
        }}

        .status-title {{
            color: var(--text-main);
            font-size: 16px;
            font-weight: 900;
            margin-bottom: 4px;
        }}

        .status-message {{
            color: var(--text-muted);
            font-size: 13px;
        }}

        .section-spacer {{
            height: 24px;
        }}

        .table-card {{
            padding: 20px 24px;
            margin-bottom: 12px;
        }}

        .card-title {{
            color: var(--text-main);
            font-size: 16px;
            font-weight: 900;
        }}

        .card-subtitle {{
            color: var(--text-muted);
            font-size: 12px;
            margin-top: 4px;
        }}

        /* Top Page Actions */
        div[data-testid="column"] .stButton > button {{
            min-height: 36px;
            height: 36px;
            min-width: 36px;
            border-radius: 10px;
            background: var(--surface);
            border: 1px solid var(--card-border);
            color: var(--text-main);
        }}

        div[data-testid="column"] .stButton > button:hover {{
            background: var(--primary-soft);
            border-color: var(--primary-border);
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )