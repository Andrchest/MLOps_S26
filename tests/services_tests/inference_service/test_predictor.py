import unittest
from unittest.mock import MagicMock, patch
from services.inference_service import predictor


class TestPredictor(unittest.TestCase):
    def setUp(self):
        self.mock_model = MagicMock()
        self.mock_model.predict.return_value = [1]
        self.mock_model.predict_proba.return_value = [[0.1, 0.9]]
        self.dummy_bytes = b"fake_model_data"

    def test_predict_returns_correct_types(self):
        """Ensure the predictor parses input and returns (int, float)."""
        # Patch the joblib attribute directly on the loaded module object
        with patch.object(
            predictor.joblib, "load", return_value=self.mock_model
        ):
            model_predictor = predictor.Predictor(self.dummy_bytes)
            input_data = {"age": 30, "monthly_spend": 50.0, "tenure_months": 12}

            label, score = model_predictor.predict(input_data)

            self.assertIsInstance(label, int)
            self.assertIsInstance(score, float)
            self.assertEqual(label, 1)

    def test_model_caching(self):
        """Verify that get_cached_model actually uses the lru_cache."""
        predictor.get_cached_model.cache_clear()

        # Patching the 'joblib' inside the module
        with patch.object(
            predictor.joblib, "load", return_value=self.mock_model
        ) as mock_load:
            # First call: Should be a miss
            predictor.get_cached_model(self.dummy_bytes)
            self.assertEqual(predictor.get_cached_model.cache_info().misses, 1)

            # Second call: Should be a hit
            predictor.get_cached_model(self.dummy_bytes)
            self.assertEqual(predictor.get_cached_model.cache_info().hits, 1)

            # Ensure joblib.load was only called once
            self.assertEqual(mock_load.call_count, 1)


if __name__ == "__main__":
    unittest.main()
