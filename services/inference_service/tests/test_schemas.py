import pytest
from schemas import InputData, Prediction, PredictResponse
from datetime import datetime


def test_input_data_validation():
    # Valid data
    data = {"age": 25, "monthly_spend": 500.5, "tenure_months": 10}
    input_obj = InputData(**data)
    assert input_obj.age == 25
    assert input_obj.monthly_spend == 500.5
    assert input_obj.tenure_months == 10

    # Invalid data (age should be int, monthly_spend float)
    with pytest.raises(ValueError):
        InputData(age="not_an_int", monthly_spend=500.5, tenure_months=10)


def test_prediction_validation():
    prediction = Prediction(label=1, score=0.95)
    assert prediction.label == 1
    assert prediction.score == 0.95


def test_predict_response_validation():
    input_data = InputData(age=30, monthly_spend=100.0, tenure_months=12)
    prediction = Prediction(label=0, score=0.1)
    now = datetime.now()

    response = PredictResponse(
        request_id="uuid-123",
        timestamp=now,
        model_version="v1",
        model_name="my_model",
        input_data=input_data,
        prediction=prediction,
        latency_ms=50,
        status="success",
    )

    assert response.request_id == "uuid-123"
    assert response.input_data.age == 30
    assert response.prediction.label == 0
