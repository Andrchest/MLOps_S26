import pandas as pd

import repository


def test_safe_query_to_df_success(monkeypatch):
    class DummyConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def mock_get_connection():
        return DummyConnection()

    def mock_read_sql_query(query, conn):
        return pd.DataFrame([{"job_id": 1, "status": "pending"}])

    monkeypatch.setattr(repository, "get_connection", mock_get_connection)
    monkeypatch.setattr(pd, "read_sql_query", mock_read_sql_query)

    result = repository.safe_query_to_df("SELECT 1")

    assert result["ok"] is True
    assert result["error"] is None
    assert not result["data"].empty
    assert list(result["data"].columns) == ["job_id", "status"]


def test_safe_query_to_df_failure(monkeypatch):
    class DummyConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def mock_get_connection():
        return DummyConnection()

    def mock_read_sql_query(query, conn):
        raise Exception("db failure")

    monkeypatch.setattr(repository, "get_connection", mock_get_connection)
    monkeypatch.setattr(pd, "read_sql_query", mock_read_sql_query)

    result = repository.safe_query_to_df("SELECT 1")

    assert result["ok"] is False
    assert result["data"].empty
    assert "db failure" in result["error"]


def test_get_datasets_placeholder():
    result = repository.get_datasets()

    assert result["ok"] is True
    assert result["data"].empty
    assert result["source"] == "placeholder"
    assert "pending" in result["message"].lower()


def test_get_deployments_placeholder():
    result = repository.get_deployments()

    assert result["ok"] is True
    assert result["data"].empty
    assert result["source"] == "placeholder"
    assert "pending" in result["message"].lower()


def test_get_service_health_returns_dataframe(monkeypatch):
    class DummyResponse:
        def __init__(self, status_code):
            self.status_code = status_code

    def mock_get(url, timeout):
        return DummyResponse(200)

    monkeypatch.setattr(repository.requests, "get", mock_get)

    result = repository.get_service_health()

    assert result["ok"] is True
    assert not result["data"].empty
    assert "service" in result["data"].columns
    assert "status" in result["data"].columns
    assert set(result["data"]["status"]) == {"healthy"}
