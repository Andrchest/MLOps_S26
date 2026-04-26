import streamlit as st


def render_status_badge(status):
    colors = {
        "pending": "🟡",
        "running": "🔵",
        "succeeded": "🟢",
        "failed": "🔴",
        "success": "🟢",
        "active": "🟢",
        "inactive": "⚪",
        "rolled_back": "🟣",
        "healthy": "🟢",
        "degraded": "🟡",
        "down": "🔴",
    }

    if status is None:
        return "⚪ unknown"

    status_text = str(status)
    return f"{colors.get(status_text.lower(), '⚪')} {status_text}"


def apply_status_badges(df):
    if "status" in df.columns:
        df = df.copy()
        df["status"] = df["status"].apply(render_status_badge)

    return df


def render_table(result, title, empty_message):
    st.subheader(title)

    if not result["ok"]:
        st.error(result["error"])
        return

    df = result["data"]

    if df.empty:
        st.info(empty_message)
        return

    df = apply_status_badges(df)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_metric(label, value):
    st.metric(label, value)


def render_health_table(result):
    render_table(
        result,
        "System Health",
        "No service health data available.",
    )