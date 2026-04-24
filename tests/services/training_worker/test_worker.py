import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch

import services.training_worker.worker as worker_module

fake_job = {
    "job_id": 1,
    "dataset_name": "data",
    "dataset_id": 10,
}


def setup_tmp_file():
    os.makedirs("/tmp", exist_ok=True)

    # cleanup before
    if os.path.exists("/tmp/data"):
        os.remove("/tmp/data")
    if os.path.exists("/tmp/data.csv"):
        os.remove("/tmp/data.csv")

    with open("/tmp/data", "w") as f:
        f.write("test")


# =========================
# SUCCESS CASE
# =========================
@pytest.mark.asyncio
@patch("services.training_worker.worker.update_status", new_callable=AsyncMock)
@patch("services.training_worker.worker.save_trained_model", new_callable=AsyncMock)
@patch("services.training_worker.worker.save_model_to_minio")
@patch("services.training_worker.worker.download_dataset")
@patch("services.training_worker.worker.MlflowClient")
@patch("services.training_worker.worker.mlflow.get_experiment_by_name")
@patch("services.training_worker.worker.mlflow.artifacts.download_artifacts")
@patch("services.training_worker.worker.mlflow.sklearn.load_model")
@patch("services.training_worker.worker.subprocess.run")
async def test_process_job_success(
    mock_subprocess,
    mock_load_model,
    mock_download_artifacts,
    mock_get_experiment,
    mock_mlflow_client,
    mock_download_dataset,
    mock_save_minio,
    mock_save_db,
    mock_update_status,
):
    # -------------------------
    # setup file
    # -------------------------
    setup_tmp_file()

    # -------------------------
    # subprocess success
    # -------------------------
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = "OK"

    # -------------------------
    # experiment
    # -------------------------
    mock_exp = MagicMock()
    mock_exp.experiment_id = "1"
    mock_get_experiment.return_value = mock_exp

    # -------------------------
    # mlflow run
    # -------------------------
    mock_run = MagicMock()
    mock_run.info.run_id = "run123"
    mock_run.data.params = {"model_type": "LogisticRegression"}
    mock_run.data.metrics = {"acc": 0.95}

    mock_client_instance = MagicMock()
    mock_client_instance.search_runs.return_value = [mock_run]
    mock_mlflow_client.return_value = mock_client_instance

    # -------------------------
    # artifacts + model
    # -------------------------
    mock_download_artifacts.return_value = "/tmp/model.joblib"
    mock_load_model.return_value = MagicMock()
    mock_save_minio.return_value = "models/model.joblib"

    # -------------------------
    # RUN
    # -------------------------
    await worker_module.process_job(fake_job)

    # -------------------------
    # ASSERT
    # -------------------------
    mock_update_status.assert_any_call(1, "succeeded")


# =========================
# FAIL CASE
# =========================
@pytest.mark.asyncio
@patch("services.training_worker.worker.update_status", new_callable=AsyncMock)
@patch("services.training_worker.worker.download_dataset")
@patch("services.training_worker.worker.subprocess.run")
async def test_process_job_fail(
    mock_subprocess,
    mock_download_dataset,
    mock_update_status,
):
    # -------------------------
    # setup file
    # -------------------------
    setup_tmp_file()

    # -------------------------
    # download mock
    # -------------------------
    mock_download_dataset.return_value = None

    # -------------------------
    # subprocess fail
    # -------------------------
    mock_subprocess.return_value.returncode = 1
    mock_subprocess.return_value.stderr = "error"

    # -------------------------
    # RUN (без pytest.raises)
    # -------------------------
    await worker_module.process_job(fake_job)

    # -------------------------
    # ASSERT
    # -------------------------
    mock_update_status.assert_any_call(1, "failed")
