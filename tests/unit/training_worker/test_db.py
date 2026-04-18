import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import sys
import os

# Add the services directory to sys.path so we can import from it
sys.path.append("/home/andreipc/MLOps/MLOps_S26/services/training_worker")
# Also add the root of the project to ensure imports work
sys.path.append("/home/andreipc/MLOps/MLOps_S26")

from db import get_job, update_status, save_trained_model
import db


@pytest.mark.asyncio
async def test_get_job():
    mock_conn = AsyncMock()
    mock_conn.fetchrow.return_value = {
        "job_id": 1,
        "dataset_name": "test",
        "dataset_id": "d1",
    }
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    db.db_pool = mock_pool

    job = await get_job()

    assert job == {"job_id": 1, "dataset_name": "test", "dataset_id": "d1"}
    mock_conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_update_status():
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    db.db_pool = mock_pool

    await update_status(1, "succeeded")

    mock_conn.execute.assert_called_once_with(
        "UPDATE jobs SET status=$1 WHERE job_id=$2", "succeeded", 1
    )


@pytest.mark.asyncio
async def test_save_trained_model():
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    db.db_pool = mock_pool

    metrics = {"accuracy": 0.95}
    params = {"lr": 0.01}

    await save_trained_model(
        job_id=1,
        model_name="test_model",
        model_version="v1",
        model_path="/tmp/model",
        metrics=metrics,
        parameters=params,
    )

    mock_conn.execute.assert_called_once()
    args = mock_conn.execute.call_args[0]
    # Check that it's an INSERT statement
    assert "INSERT INTO trained_models" in args[0].strip().replace("\n", " ")
    assert args[1] == 1
    assert args[2] == "test_model"
    assert args[3] == "v1"
    assert args[4] == "/tmp/model"
    assert args[5] == json.dumps(metrics)
    assert args[6] == json.dumps(params)
