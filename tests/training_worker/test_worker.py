import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import services.training_worker.worker as worker_module


FAKE_JOB = {
    "job_id": 1,
    "dataset_name": "data.csv",
    "dataset_id": 10,
}

FAKE_JOB_WITH_PATH = {
    "job_id": 2,
    "dataset_name": "data.csv",
    "dataset_id": 11,
    "dataset_path": "datasets/breast_cancer/hash123.csv",
}


def _build_mock_run(run_id: str, metrics: dict[str, float]) -> MagicMock:
    run = MagicMock()
    run.info.run_id = run_id
    run.data.params = {"model_type": "LogisticRegression"}
    run.data.metrics = metrics
    return run


@pytest.mark.asyncio
@patch("services.training_worker.worker.update_status", new_callable=AsyncMock)
@patch("services.training_worker.worker.save_trained_model", new_callable=AsyncMock)
@patch("services.training_worker.worker.save_model_to_minio")
@patch("services.training_worker.worker.download_dataset")
@patch("services.training_worker.worker.MlflowClient")
@patch("services.training_worker.worker.mlflow.get_experiment_by_name")
@patch("services.training_worker.worker.mlflow.artifacts.download_artifacts")
@patch("services.training_worker.worker.subprocess.run")
async def test_process_job_success(
    mock_subprocess,
    mock_download_artifacts,
    mock_get_experiment,
    mock_mlflow_client,
    mock_download_dataset,
    mock_save_minio,
    mock_save_db,
    mock_update_status,
):
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = "OK"
    mock_subprocess.return_value.stderr = ""

    mock_exp = MagicMock()
    mock_exp.experiment_id = "1"
    mock_get_experiment.return_value = mock_exp

    mock_client_instance = MagicMock()
    mock_client_instance.search_runs.return_value = [
        _build_mock_run("run123", {"accuracy": 0.95})
    ]
    mock_mlflow_client.return_value = mock_client_instance

    mock_download_artifacts.return_value = "/tmp/model.joblib"
    mock_save_minio.return_value = "models/model.joblib"

    await worker_module.process_job(FAKE_JOB)

    mock_download_dataset.assert_called_once_with("data.csv", "/tmp/data.csv")
    mock_update_status.assert_any_call(1, "persisting")
    mock_update_status.assert_any_call(1, "succeeded")


@pytest.mark.asyncio
@patch("services.training_worker.worker.update_status", new_callable=AsyncMock)
@patch("services.training_worker.worker.download_dataset")
@patch("services.training_worker.worker.subprocess.run")
async def test_process_job_marks_failed_on_pipeline_error(
    mock_subprocess,
    mock_download_dataset,
    mock_update_status,
):
    mock_download_dataset.return_value = None
    mock_subprocess.return_value.returncode = 1
    mock_subprocess.return_value.stderr = "error"
    mock_subprocess.return_value.stdout = ""

    await worker_module.process_job(FAKE_JOB)

    mock_update_status.assert_any_call(1, "failed")


@pytest.mark.asyncio
@patch("services.training_worker.worker.update_status", new_callable=AsyncMock)
@patch("services.training_worker.worker.save_trained_model", new_callable=AsyncMock)
@patch("services.training_worker.worker.save_model_to_minio")
@patch("services.training_worker.worker.download_dataset")
@patch("services.training_worker.worker.MlflowClient")
@patch("services.training_worker.worker.mlflow.get_experiment_by_name")
@patch("services.training_worker.worker.mlflow.artifacts.download_artifacts")
@patch("services.training_worker.worker.subprocess.run")
async def test_process_job_uses_dataset_path_when_present(
    mock_subprocess,
    mock_download_artifacts,
    mock_get_experiment,
    mock_mlflow_client,
    mock_download_dataset,
    mock_save_minio,
    mock_save_db,
    mock_update_status,
):
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = "OK"
    mock_subprocess.return_value.stderr = ""

    mock_exp = MagicMock()
    mock_exp.experiment_id = "1"
    mock_get_experiment.return_value = mock_exp

    mock_client_instance = MagicMock()
    mock_client_instance.search_runs.return_value = [
        _build_mock_run("run456", {"accuracy": 0.91})
    ]
    mock_mlflow_client.return_value = mock_client_instance

    mock_download_artifacts.return_value = "/tmp/model.joblib"
    mock_save_minio.return_value = "models/model.joblib"

    await worker_module.process_job(FAKE_JOB_WITH_PATH)

    mock_download_dataset.assert_called_once_with(
        "datasets/breast_cancer/hash123.csv",
        "/tmp/hash123.csv",
    )
