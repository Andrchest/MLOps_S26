import pandas as pd
import streamlit as st


def render_result(result: dict, title: str, empty_message: str) -> None:
    st.subheader(title)

    if not result["ok"]:
        st.error(result["error"])
        return

    df = result["data"]
    if df.empty:
        st.info(empty_message)
        return

    st.dataframe(df, use_container_width=True, hide_index=True)
