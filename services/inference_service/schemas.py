from pydantic import BaseModel
from datetime import datetime


class InputData(BaseModel):
    age: int
    monthly_spend: float
    tenure_months: int
    income: float
    credit_score: int


class Prediction(BaseModel):
    label: int
    score: float


class PredictResponse(BaseModel):
    request_id: str
    timestamp: datetime
    model_version: str
    model_name: str
    input_data: InputData
    prediction: Prediction
    latency_ms: int
    status: str
