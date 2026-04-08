import joblib
import pandas as pd
from pathlib import Path


class ChurnPredictor:
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self.model = self._load_model()

    def _load_model(self):
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        return joblib.load(self.model_path)

    def predict(self, input_data: dict):
        X = pd.DataFrame([input_data])
        label = int(self.model.predict(X)[0])
        score = float(self.model.predict_proba(X)[0][label])
        return label, score
