import pytest
from unittest.mock import AsyncMock, patch

from services.training_worker.worker import worker_loop


@pytest.mark.asyncio
async def test_no_duplicate_jobs():
    jobs = [
        {"job_id": 1, "dataset_name": "a", "dataset_id": 1},
        None,
    ]

    async def fake_get_job():
        return jobs.pop(0)

    with patch("services.training_worker.worker.get_job", new=fake_get_job):
        with patch(
            "services.training_worker.worker.process_job", new_callable=AsyncMock
        ) as mock_proc:
            with patch(
                "services.training_worker.worker.recover_stuck_jobs",
                new_callable=AsyncMock,
            ):

                # ❗ Важно: не даём бесконечному циклу зависнуть
                with patch(
                    "asyncio.sleep",
                    new_callable=AsyncMock,
                    side_effect=Exception("stop"),
                ):
                    try:
                        await worker_loop()
                    except Exception:
                        pass

    mock_proc.assert_called_once()
