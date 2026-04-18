import pytest
from unittest.mock import MagicMock, patch
import io
import numpy as np
from predictor import Predictor


@pytest.fixture
def mock_model():
    model = MagicMock()
    # Mock predict to return [1]
    model.predict.return_value = np.array([1])
    # Mock predict_proba to return [[0.2, 0.8]]
    model.predict_proba.return_value = np.array([[0.2, 0.8]])
    return model


@pytest.fixture
def model_bytes():
    return b"dummy_model_bytes"


def test_predictor_init_and_predict(mock_model, model_bytes):
    with patch("predictor.joblib.load") as mock_joblib_load:
        mock_joblib_load.return_value = mock_model

        predictor = Predictor(model_bytes)

        # Verify model was loaded
        mock_joblib_load.assert_called_once()

        # Test prediction
        input_data = {"age": 30, "monthly_spend": 100.0, "tenure_months": 12}
        label, score = predictor.predict(input_data)

        assert label == 1
        assert score == 0.8

        # Verify model calls
        # predictor.predict(X) where X is a DataFrame
        # model.predict(X) should be called
        assert mock_model.predict.called
        assert mock_model.predict_proba.called
