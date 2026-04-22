import runpy

import pytest


def test_app_handles_db_down(monkeypatch):
    import db
    import streamlit as st

    calls = {"error": [], "info": [], "stop": 0}

    monkeypatch.setattr(db, "check_db_health", lambda: (False, "Database down"))

    monkeypatch.setattr(st, "set_page_config", lambda **kwargs: None)
    monkeypatch.setattr(st, "title", lambda *args, **kwargs: None)
    monkeypatch.setattr(st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        st,
        "sidebar",
        type("Sidebar", (), {"radio": lambda *args, **kwargs: "System Overview"})(),
    )
    monkeypatch.setattr(st, "error", lambda msg: calls["error"].append(msg))
    monkeypatch.setattr(st, "info", lambda msg: calls["info"].append(msg))

    def fake_stop():
        calls["stop"] += 1
        raise RuntimeError("streamlit stop")

    monkeypatch.setattr(st, "stop", fake_stop)

    with pytest.raises(RuntimeError, match="streamlit stop"):
        runpy.run_path("app.py", run_name="__main__")

    assert calls["stop"] == 1
    assert any("Database unavailable" in msg for msg in calls["error"])
    assert any("DB-backed data cannot be loaded" in msg for msg in calls["info"])
