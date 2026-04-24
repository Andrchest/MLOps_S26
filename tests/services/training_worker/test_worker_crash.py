import pytest
from unittest.mock import AsyncMock, patch
from services.training_worker import worker


@pytest.mark.asyncio
@patch("services.training_worker.worker.update_status", new_callable=AsyncMock)
@patch("services.training_worker.worker.download_dataset")
@patch("services.training_worker.worker.subprocess.run")
async def test_worker_crash(
    mock_subprocess,
    mock_download,
    mock_update_status,
):
    job = {
        "job_id": 1,
        "dataset_name": "data",
        "dataset_id": 1,
    }

    mock_subprocess.side_effect = Exception("crash")

    await worker.process_job(job)

    mock_update_status.assert_any_call(1, "failed")
