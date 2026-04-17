from io import BytesIO
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import services.orchestrator.app as orchestrator_app
import services.orchestrator.dataset_service as dataset_service


client = TestClient(orchestrator_app.app)


def _post_dataset(filename: str = "breast_cancer.csv", content: bytes = b"a,b,target\n1,2,0\n"):
    return client.post(
        "/datasets",
        files={"file": (filename, BytesIO(content), "text/csv")},
    )


def setup_function():
    orchestrator_app.dataset_registry.reset()


def test_duplicate_uploads_are_idempotent(monkeypatch):
    put_object = MagicMock()
    exists_counter = {"count": 0}

    def fake_object_exists(bucket_name, object_name):
        exists_counter["count"] += 1
        return exists_counter["count"] > 1

    monkeypatch.setattr(orchestrator_app.storage_client, "ensure_bucket", lambda bucket_name: None)
    monkeypatch.setattr(orchestrator_app.storage_client, "object_exists", fake_object_exists)
    monkeypatch.setattr(orchestrator_app.storage_client.client, "put_object", put_object)

    first_response = _post_dataset()
    second_response = _post_dataset()

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["dataset_id"] == second_response.json()["dataset_id"]
    assert first_response.json()["path"] == second_response.json()["path"]
    assert put_object.call_count == 1


def test_failed_upload_recovers_with_retry(monkeypatch):
    put_object = MagicMock(side_effect=[Exception("temporary failure"), MagicMock()])

    monkeypatch.setattr(orchestrator_app.storage_client, "ensure_bucket", lambda bucket_name: None)
    monkeypatch.setattr(orchestrator_app.storage_client, "object_exists", lambda bucket_name, object_name: False)
    monkeypatch.setattr(orchestrator_app.storage_client.client, "put_object", put_object)
    monkeypatch.setattr(dataset_service.time, "sleep", lambda _: None)

    response = _post_dataset()

    assert response.status_code == 200
    assert put_object.call_count == 2
    assert response.json()["dataset_id"] == 1


def test_minio_unavailability_returns_503(monkeypatch):
    put_object = MagicMock(side_effect=Exception("minio unavailable"))

    monkeypatch.setattr(orchestrator_app.storage_client, "ensure_bucket", lambda bucket_name: None)
    monkeypatch.setattr(orchestrator_app.storage_client, "object_exists", lambda bucket_name, object_name: False)
    monkeypatch.setattr(orchestrator_app.storage_client.client, "put_object", put_object)
    monkeypatch.setattr(dataset_service.time, "sleep", lambda _: None)

    response = _post_dataset()

    assert response.status_code == 503
    assert "Failed to upload dataset" in response.json()["detail"]
    assert orchestrator_app.dataset_registry.get(1) is None
