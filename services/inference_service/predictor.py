import joblib
import pandas as pd
import io
from functools import lru_cache


# This cache lives inside each worker process
@lru_cache(maxsize=10)
def get_cached_model(model_bytes: bytes):
    return joblib.load(io.BytesIO(model_bytes))


class Predictor:
    def __init__(self, model_bytes: bytes):
        self.model = get_cached_model(model_bytes)

    def predict(self, input_data: dict):
        X = pd.DataFrame([input_data])
        label = int(self.model.predict(X)[0])
        score = float(self.model.predict_proba(X)[0][label])
        return label, score
