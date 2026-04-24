import sys
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

# Ensure the service directory is in the path
sys.path.append("/home/andreipc/MLOps/MLOps_S26/services/inference-service")

from predictor import Predictor


@pytest.fixture
def mock_model_bytes():
    return b"fake_model_bytes"


@pytest.fixture
def mock_predictor(mock_model_bytes):
    with patch("predictor.get_cached_model") as mock_get_cached:
        # Create a mock model object
        mock_model = MagicMock()
        # Mock predict and predict_proba
        # predict returns [label]
        mock_model.predict.return_value = [1]
        # predict_proba returns [[prob0, prob1]]
        mock_model.predict_proba.return_value = [[0.2, 0.8]]

        mock_get_cached.return_value = mock_model

        predictor = Predictor(mock_model_bytes)
        yield predictor, mock_get_cached, mock_model


def test_predictor_predict(mock_predictor):
    predictor, mock_get_cached, mock_model = mock_predictor
    input_data = {"feature1": 1.0, "feature2": 2.0}

    # Execute
    label, score = predictor.predict(input_data)

    # Verify
    assert label == 1
    assert score == 0.8

    # Verify model calls
    # Check if predict was called with a DataFrame
    args, _ = mock_model.predict.call_args
    called_df = args[0]
    assert isinstance(called_df, pd.DataFrame)
    assert called_df.iloc[0]["feature1"] == 1.0

    # Check if predict_proba was called
    mock_model.predict_proba.assert_called_once()


def test_predictor_init(mock_model_bytes):
    with patch("predictor.get_cached_model") as mock_get_cached:
        mock_model = MagicMock()
        mock_get_cached.return_value = mock_model

        predictor = Predictor(mock_model_bytes)

        assert predictor.model == mock_model
        mock_get_cached.assert_called_once_with(mock_model_bytes)
