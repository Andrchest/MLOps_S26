import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import importlib.util
import sys
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parents[3]
app_dir = project_root / "services" / "inference_service"

# Ensure app_dir is in sys.path for bare imports within app.py
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

spec = importlib.util.spec_from_file_location("app_module", str(app_dir / "app.py"))
app_module = importlib.util.module_from_spec(spec)
sys.modules["app_module"] = app_module
spec.loader.exec_module(app_module)

application = app_module.app


class TestAPI(unittest.TestCase):
    def setUp(self):
        # Ensure model_executor exists on the module
        if not hasattr(app_module, "model_executor"):
            app_module.model_executor = MagicMock()

        self.test_ctx = TestClient(application)
        self.client = self.test_ctx.__enter__()

    def tearDown(self):
        self.test_ctx.__exit__(None, None, None)

    @patch("load_model.fetch_model_with_retry", new_callable=AsyncMock)
    @patch("app_module._run_prediction", return_value=(1, 0.95))
    def test_predict_success(self, mock_run, mock_fetch):
        """Test a successful prediction."""
        mock_fetch.return_value = b"fake_model_bytes"

        async def side_effect_executor(executor, func, *args):
            return func(*args)

        app_module.model_executor.run_in_executor = MagicMock(
            side_effect=side_effect_executor
        )

        payload = {"age": 25, "monthly_spend": 50.0, "tenure_months": 12}
        response = self.client.post(
            "/predict?model_name=m1&model_version=v1", json=payload
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["prediction"]["label"], 1)
        self.assertEqual(data["prediction"]["score"], 0.95)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["model_name"], "m1")

    @patch("load_model.fetch_model_with_retry", new_callable=AsyncMock)
    def test_predict_model_not_found(self, mock_fetch):
        """Test 404 when model is not found."""
        mock_fetch.side_effect = ValueError("Model not found")

        payload = {"age": 25, "monthly_spend": 50.0, "tenure_months": 12}
        response = self.client.post(
            "/predict?model_name=invalid&model_version=v1", json=payload
        )

        self.assertEqual(response.status_code, 404)

    def test_predict_invalid_payload(self):
        """Test 422 when payload is invalid."""
        payload = {"age": "not_an_int", "monthly_spend": 50.0, "tenure_months": 12}
        response = self.client.post(
            "/predict?model_name=m1&model_version=v1", json=payload
        )
        self.assertEqual(response.status_code, 422)

    @patch("load_model.fetch_model_with_retry", new_callable=AsyncMock)
    def test_predict_internal_error(self, mock_fetch):
        """Test 500 when an exception occurs during prediction."""
        mock_fetch.return_value = b"fake_model_bytes"

        async def side_effect_executor(executor, func, *args):
            return func(*args)

        app_module.model_executor.run_in_executor = MagicMock(
            side_effect=side_effect_executor
        )

        with patch(
            "app_module._run_prediction", side_effect=Exception("Unexpected error")
        ):
            payload = {"age": 25, "monthly_spend": 50.0, "tenure_months": 12}
            response = self.client.post(
                "/predict?model_name=m1&model_version=v1", json=payload
            )

            self.assertEqual(response.status_code, 500)

    def test_health(self):
        """Test health endpoint."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
