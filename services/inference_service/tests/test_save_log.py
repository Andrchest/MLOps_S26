import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app import save_log
from schemas import PredictResponse, Prediction, InputData
from datetime import datetime
import uuid


@pytest.mark.asyncio
async def test_save_log_success():
    # Setup
    input_data = InputData(age=30, monthly_spend=100.0, tenure_months=12)
    prediction = Prediction(label=1, score=0.9)
    response = PredictResponse(
        request_id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        model_version="v1",
        model_name="test_model",
        input_data=input_data,
        prediction=prediction,
        latency_ms=50,
        status="success",
    )

    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    with patch("app.db_pool", mock_pool):
        await save_log(response)

    # Verify
    mock_conn.execute.assert_called_once()
    args, _ = mock_conn.execute.call_args
    query = args[0]
    params = args[1:]

    assert "INSERT INTO prediction_logs" in query
    assert params[0] == response.request_id
    assert params[1] == response.timestamp
    assert params[2] == response.model_version
    assert params[3] == response.model_name
    assert params[4] == '{"age": 30, "monthly_spend": 100.0, "tenure_months": 12}'
    assert params[5] == '{"label": 1, "score": 0.9}'
    assert params[6] == 50
    assert params[7] == "success"


@pytest.mark.asyncio
async def test_save_log_failure():
    # Setup
    input_data = InputData(age=30, monthly_spend=100.0, tenure_months=12)
    prediction = Prediction(label=1, score=0.9)
    response = PredictResponse(
        request_id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        model_version="v1",
        model_name="test_model",
        input_data=input_data,
        prediction=prediction,
        latency_ms=50,
        status="success",
    )

    mock_pool = MagicMock()
    mock_pool.acquire.side_effect = Exception("DB connection failed")

    with patch("app.db_pool", mock_pool):
        # Should not raise exception, but print "FAILED: ..."
        await save_log(response)

    # If it didn't raise, the test passes.
