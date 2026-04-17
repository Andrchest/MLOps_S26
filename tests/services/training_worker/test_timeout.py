import pytest
import subprocess
import os
from unittest.mock import patch, AsyncMock

from services.training_worker import worker


@pytest.mark.asyncio
@patch("services.training_worker.worker.update_status", new_callable=AsyncMock)
@patch("services.training_worker.worker.download_dataset")
@patch("services.training_worker.worker.subprocess.run")
async def test_timeout(
    mock_subprocess,
    mock_download,
    mock_update_status,
):
    job = {
        "job_id": 1,
        "dataset_name": "data",
        "dataset_id": 1,
    }

    # -------------------------
    # Создаём fake файл (ВАЖНО)
    # -------------------------
    os.makedirs("/tmp", exist_ok=True)
    with open("/tmp/data", "w") as f:
        f.write("test")

    # -------------------------
    # subprocess timeout
    # -------------------------
    mock_subprocess.side_effect = subprocess.TimeoutExpired(cmd="cmd", timeout=1)

    # -------------------------
    # RUN
    # -------------------------
    await worker.process_job(job)

    # -------------------------
    # ASSERT
    # -------------------------
    mock_update_status.assert_any_call(1, "failed")
