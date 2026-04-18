import sys
from unittest.mock import MagicMock

# Mock modules before they are imported
sys.modules["mlflow"] = MagicMock()
sys.modules["mlflow.tracking"] = MagicMock()
sys.modules["mlflow.artifacts"] = MagicMock()
sys.modules["minio"] = MagicMock()
sys.modules["asyncpg"] = MagicMock()

# Mock minio_client to point to a fake module, then we patch it
fake_minio_client = MagicMock()
fake_minio_client.DATASETS_BUCKET = "datasets"
fake_minio_client.MODELS_BUCKET = "models"
fake_minio_client.minio_client = MagicMock()
sys.modules["minio_client"] = fake_minio_client

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import subprocess
import os
import asyncio
import shutil

# Add the services directory to sys.path so we can import from it
sys.path.insert(0, "/home/andreipc/MLOps/MLOps_S26/services/training_worker")
# Also add the root of the project to ensure imports work
sys.path.insert(0, "/home/andreipc/MLOps/MLOps_S26")

from worker import process_job, worker_loop
import mlflow


@pytest.mark.asyncio
@patch("worker.update_status", new_callable=AsyncMock)
@patch("worker.save_trained_model", new_callable=AsyncMock)
@patch("worker.download_dataset")
@patch("worker.save_model_to_minio")
@patch("worker.subprocess.run")
@patch("worker.MlflowClient")
@patch("worker.mlflow")
@patch("worker.os.makedirs")
@patch("shutil.move")
async def test_process_job_success(
    mock_shutil_move,
    mock_os_makedirs,
    mock_mlflow,
    mock_mlflow_client,
    mock_subprocess_run,
    mock_save_model_to_minio,
    mock_download_dataset,
    mock_save_trained_model,
    mock_update_status,
):
    # Setup job
    job = {"job_id": 123, "dataset_name": "test_dataset", "dataset_id": "d456"}

    # Mock subprocess.run
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Success"
    mock_result.stderr = ""
    mock_subprocess_run.return_value = mock_result

    # Mock MLflow client and search_runs
    mock_client_instance = mock_mlflow_client.return_value
    mock_run = MagicMock()
    mock_run.info.run_id = "run_789"
    mock_run.data.params = {"model_type": "resnet"}
    mock_run.data.metrics = {"accuracy": 0.9}
    mock_client_instance.search_runs.return_value = [mock_run]

    # Mock mlflow.get_experiment_by_name
    mock_experiment = MagicMock()
    mock_experiment.experiment_id = "exp_001"
    mock_mlflow.get_experiment_by_name.return_value = mock_experiment

    # Mock download_artifacts using the mocked mlflow
    mock_mlflow.artifacts.download_artifacts.return_value = "/tmp/model_dir"

    # Mock save_model_to_minio
    mock_save_model_to_minio.return_value = "minio_path/model.joblib"

    # Execute
    await process_job(job)

    # Verifications
    mock_download_dataset.assert_called_once_with("test_dataset", "/tmp/test_dataset")
    mock_subprocess_run.assert_called_once()
    mock_update_status.assert_any_call(123, "persisting")
    mock_save_model_to_minio.assert_called_once_with(
        local_model_path="/tmp/model_dir",
        model_name="resnet",
        model_version="123_d456_run_789",
    )
    mock_save_trained_model.assert_called_once()
    mock_update_status.assert_any_call(123, "succeeded")


@pytest.mark.asyncio
@patch("worker.update_status", new_callable=AsyncMock)
@patch("worker.download_dataset")
@patch("worker.subprocess.run")
async def test_process_job_pipeline_failure(
    mock_subprocess_run,
    mock_download_dataset,
    mock_update_status,
):
    # Setup job
    job = {"job_id": 123, "dataset_name": "test_dataset", "dataset_id": "d456"}

    # Mock subprocess.run failure
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Error in pipeline"
    mock_subprocess_run.return_value = mock_result

    # Execute
    await process_job(job)

    # Verifications
    mock_update_status.assert_called_once_with(123, "failed")


@pytest.mark.asyncio
@patch("worker.get_job", new_callable=AsyncMock)
@patch("worker.asyncio.sleep", new_callable=AsyncMock)
@patch("worker.process_job", new_callable=AsyncMock)
async def test_worker_loop_calls_process(mock_process_job, mock_sleep, mock_get_job):
    # We want to test that the loop calls process_job when a job is returned
    # and then sleeps. Since it's an infinite loop, we make sleep raise an exception to break it.

    job = {"job_id": 1, "dataset_name": "ds", "dataset_id": "id"}
    mock_get_job.return_value = job
    mock_sleep.side_effect = asyncio.CancelledError("Stop loop")

    try:
        await worker_loop()
    except asyncio.CancelledError:
        pass

    mock_get_job.assert_called_once()
    mock_process_job.assert_called_once_with(job)
    mock_sleep.assert_called_once()
