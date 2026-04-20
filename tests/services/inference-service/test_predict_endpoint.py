import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
import importlib.util
from pathlib import Path
import sys
import asyncio

current_file = Path(__file__).resolve()
app_dir = current_file.parents[3] / "services" / "inference_service"
app_path = app_dir / "app.py"

if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))


spec = importlib.util.spec_from_file_location("app_module", str(app_path))
app_module = importlib.util.module_from_spec(spec)
sys.modules["app_module"] = app_module
spec.loader.exec_module(app_module)


class TestPrediction(unittest.TestCase):
    def setUp(self):
        self.test_ctx = TestClient(app_module.app)
        self.client = self.test_ctx.__enter__()

    def tearDown(self):
        app_module.model_executor.shutdown(wait=False)
        self.test_ctx.__exit__(None, None, None)

    @patch("app_module.fetch_model_with_retry", new_callable=AsyncMock)
    @patch("app_module._run_prediction")
    async def test_parallel_requests(self, mock_run, mock_fetch):

        mock_fetch.return_value = b"model"
        mock_run.return_value = (1, 0.9)

        loop = asyncio.get_running_loop()

        tasks = [
            loop.run_in_executor(
                None,
                lambda: self.client.post(
                    "/predict",
                    params={"model_name": "m", "model_version": "v1"},
                    json={
                        "age": 30,
                        "monthly_spend": 50.0,
                        "tenure_months": 10,
                        "income": 50000,
                        "credit_score": 700,
                    },
                ),
            )
            for _ in range(10)
        ]

        results = await asyncio.gather(*tasks)

        for r in results:
            self.assertEqual(r.status_code, 200)

    @patch("app_module.fetch_model_with_retry", new_callable=AsyncMock)
    @patch("app_module._run_prediction")
    async def test_predict_success(self, mock_run, mock_fetch):  # Make this async
        mock_fetch.return_value = b"model"
        mock_run.return_value = (1, 0.9)

        # Use an async client if possible, or wrap the sync call
        response = self.client.post(
            "/predict",
            params={"model_name": "m", "model_version": "v1"},
            json={
                "age": 30,
                "monthly_spend": 50.0,
                "tenure_months": 10,
                "income": 50000,
                "credit_score": 700,
            },
        )

        self.assertEqual(response.status_code, 200)

    @patch("app_module.fetch_model_with_retry", new_callable=AsyncMock)
    @patch("app_module._run_prediction")
    async def test_prediction_crash_500(self, mock_run, mock_fetch):
        mock_fetch.return_value = b"model"
        mock_run.side_effect = Exception("boom")

        # Use await if using httpx.AsyncClient,
        # otherwise TestClient call remains sync but the test handles the loop better
        response = self.client.post(
            "/predict",
            params={"model_name": "m", "model_version": "v1"},
            json={
                "age": 30,
                "monthly_spend": 50.0,
                "tenure_months": 10,
                "income": 50000,
                "credit_score": 700,
            },
        )

        self.assertEqual(response.status_code, 500)

    @patch("app_module.fetch_model_with_retry", new_callable=AsyncMock)
    async def test_minio_unavailable_returns_503(self, mock_fetch):
        # IMPORTANT: To stop the 20s delay, we override the retry wait logic
        mock_fetch.retry.wait = lambda *args, **kwargs: 0
        mock_fetch.side_effect = Exception("MinIO connection error")

        response = self.client.post(
            "/predict",
            params={"model_name": "test", "model_version": "v1"},
            json={
                "age": 30,
                "monthly_spend": 50.0,
                "tenure_months": 12,
                "income": 50000,
                "credit_score": 700,
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("unavailable", response.json()["detail"])

    @patch("app_module.fetch_model_with_retry", new_callable=AsyncMock)
    async def test_model_not_found_returns_404(self, mock_fetch):
        mock_fetch.side_effect = ValueError("Model test:v1 not found")

        response = self.client.post(
            "/predict",
            params={"model_name": "test", "model_version": "v1"},
            json={
                "age": 30,
                "monthly_spend": 50.0,
                "tenure_months": 12,
                "income": 50000,
                "credit_score": 700,
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
