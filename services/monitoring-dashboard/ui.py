import streamlit as st


def render_table(result, title, empty_message):
    st.subheader(title)

    if not result["ok"]:
        st.error(result["error"])
        return

    df = result["data"]

    if df.empty:
        st.info(empty_message)
        return

    st.dataframe(df, use_container_width=True, hide_index=True)


def render_metric(label, value):
    st.metric(label, value)


def render_status_badge(status):
    colors = {
        "pending": "🟡",
        "running": "🔵",
        "succeeded": "🟢",
        "failed": "🔴",
        "active": "🟢",
        "inactive": "⚪",
        "healthy": "🟢",
        "degraded": "🟡",
        "down": "🔴",
    }

    return f"{colors.get(status, '⚪')} {status}"


def render_health_table(result):
    st.subheader("System Health")

    if not result["ok"]:
        st.error(result["error"])
        return

    df = result["data"]

    df["status"] = df["status"].apply(render_status_badge)

    st.dataframe(df, use_container_width=True, hide_index=True)