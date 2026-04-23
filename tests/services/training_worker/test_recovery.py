import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_recover_stuck_jobs():
    with patch("services.training_worker.db.db_pool") as mock_pool:
        mock_conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

        from services.training_worker.db import recover_stuck_jobs

        await recover_stuck_jobs()

        assert mock_conn.execute.called
