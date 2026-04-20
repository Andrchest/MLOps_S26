import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path so "services.training_worker" imports work
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Mock external modules before importing worker
sys.modules["mlflow"] = MagicMock()
sys.modules["mlflow.tracking"] = MagicMock()
sys.modules["mlflow.artifacts"] = MagicMock()
sys.modules["minio"] = MagicMock()
sys.modules["minio.error"] = MagicMock()

import pytest
import asyncio
import subprocess
import shutil

from worker import process_job, worker_loop


@pytest.fixture
def mock_db():
    """Provide mocked db module."""
    mock = MagicMock()
    mock.get_job = AsyncMock()
    mock.update_status = AsyncMock()
    mock.save_trained_model = AsyncMock()
    mock.recover_stuck_jobs = AsyncMock()
    return mock


@pytest.fixture
def mock_minio_client():
    """Provide mocked minio_client module."""
    mock = MagicMock()
    mock.download_dataset = MagicMock()
    mock.save_model_to_minio = MagicMock(return_value="minio://models/test.joblib")
    mock.DATASETS_BUCKET = "datasets"
    mock.MODELS_BUCKET = "models"
    return mock


@pytest.mark.asyncio
async def test_process_job_success(mock_db, mock_minio_client):
    """Test successful job processing pipeline."""
    from unittest.mock import patch, MagicMock as MM

    job = {"job_id": 123, "dataset_name": "test_dataset", "dataset_id": "d456"}

    mock_result = MM()
    mock_result.returncode = 0
    mock_result.stdout = "Training complete"
    mock_result.stderr = ""

    mock_run = MM()
    mock_run.info.run_id = "run_789"
    mock_run.data.params = {"model_type": "logistic_regression"}
    mock_run.data.metrics = {"accuracy": 0.95}

    mock_exp = MM()
    mock_exp.experiment_id = "exp_001"

    mock_client = MM()
    mock_client.search_runs.return_value = [mock_run]

    with patch("worker.db", mock_db), \
         patch("worker.minio_client", mock_minio_client), \
         patch("worker.subprocess.run", return_value=mock_result), \
         patch("worker.MlflowClient", return_value=mock_client), \
         patch("worker.mlflow.get_experiment_by_name", return_value=mock_exp), \
         patch("worker.mlflow.artifacts.download_artifacts", return_value="/tmp/model_dir"), \
         patch("worker.asyncio.sleep", new_callable=AsyncMock), \
         patch("os.path.exists", return_value=True), \
         patch.object(shutil, "move"):

        mock_db.get_job.return_value = None  # No stuck jobs to recover

        await process_job(job)

    mock_minio_client.download_dataset.assert_called_once()
    mock_db.update_status.assert_called()
    # Check that status was set to succeeded
    calls = [str(c) for c in mock_db.update_status.call_args_list]
    assert any("succeeded" in c for c in calls)


@pytest.mark.asyncio
async def test_process_job_pipeline_failure(mock_db, mock_minio_client):
    """Test that pipeline failure marks job as failed."""
    from unittest.mock import patch, MagicMock as MM

    job = {"job_id": 123, "dataset_name": "test_dataset", "dataset_id": "d456"}

    mock_result = MM()
    mock_result.returncode = 1
    mock_result.stderr = "Pipeline error"

    with patch("worker.db", mock_db), \
         patch("worker.minio_client", mock_minio_client), \
         patch("worker.subprocess.run", return_value=mock_result), \
         patch("worker.asyncio.sleep", new_callable=AsyncMock), \
         patch("os.path.exists", return_value=True):

        mock_db.get_job.return_value = None

        await process_job(job)

    calls = [str(c) for c in mock_db.update_status.call_args_list]
    assert any("failed" in c for c in calls)


@pytest.mark.asyncio
async def test_worker_loop_calls_process():
    """Test that worker_loop polls for jobs and processes them."""
    from unittest.mock import patch, MagicMock as MM

    job = {"job_id": 1, "dataset_name": "ds", "dataset_id": "id"}
    
    mock_db = MM()
    mock_db.get_job = AsyncMock(return_value=job)
    mock_db.update_status = AsyncMock()
    mock_db.save_trained_model = AsyncMock()
    mock_db.recover_stuck_jobs = AsyncMock()

    mock_minio = MM()
    mock_minio.download_dataset = MM()
    mock_minio.save_model_to_minio = MM(return_value="minio://model.joblib")

    with patch("worker.db", mock_db), \
         patch("worker.minio_client", mock_minio), \
         patch("worker.process_job", new_callable=AsyncMock) as mock_process, \
         patch("worker.asyncio.sleep", new_callable=AsyncMock) as mock_sleep, \
         patch("worker.logging"), \
         patch("worker.asyncio", module=asyncio):

        mock_sleep.side_effect = [None, None, asyncio.CancelledError("Stop")]

        try:
            await worker_loop()
        except asyncio.CancelledError:
            pass

        mock_process.assert_called_once_with(job)
        mock_sleep.assert_called()
