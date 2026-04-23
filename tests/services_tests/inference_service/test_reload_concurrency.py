import time
import unittest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from services.inference_service import app
from concurrent.futures import ThreadPoolExecutor


class TestReloadConcurrency(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # 1. Setup DB Mocks
        self.mock_conn = AsyncMock()
        mock_acquire_ctx = MagicMock()
        mock_acquire_ctx.__aenter__ = AsyncMock(return_value=self.mock_conn)
        mock_acquire_ctx.__aexit__ = AsyncMock(return_value=None)

        self.mock_pool = MagicMock()
        self.mock_pool.acquire.return_value = mock_acquire_ctx
        self.mock_pool.close = AsyncMock()

        # This triggers the FastAPI Lifespan (Startup/Shutdown)
        self.test_ctx = TestClient(app.app)
        self.client = self.test_ctx.__enter__()

        app.model_executor = ThreadPoolExecutor(max_workers=4)

    async def asyncTearDown(self):
        self.test_ctx.__exit__(None, None, None)

    @patch("services.inference_service.minio_client.minio_client")
    async def test_reload_during_active_request(self, mock_minio):
        mock_response = MagicMock()
        mock_response.read.return_value = b"fake_model_content"
        mock_minio.get_object.return_value = mock_response

        # Check if model_executor exists, if not, wait a tiny bit for startup
        if not hasattr(app, "model_executor"):
            self.fail(
                "model_executor not found. Ensure it is initialized in the app's lifespan."
            )

        old_executor = app.model_executor

        # Mock the prediction to be slow
        def slow_prediction_mock(*args, **kwargs):
            time.sleep(5.0)
            return 1, 0.99

        with patch(
            "services.inference_service.app._run_prediction",
            side_effect=slow_prediction_mock,
        ):
            loop = asyncio.get_running_loop()
            # Run the prediction in a background thread via the client
            predict_task = loop.run_in_executor(
                None,
                lambda: self.client.post(
                    "/predict",
                    params={"model_name": "m1", "model_version": "v1"},
                    json={"age": 30, "monthly_spend": 100.0, "tenure_months": 5},
                ),
            )

            # Give the predict request time to start and hit the sleep
            await asyncio.sleep(0.5)

            # Trigger reload while predict is "sleeping"
            reload_response = self.client.post("/reload")
            self.assertEqual(reload_response.status_code, 200)

            # Verify the executor was swapped
            self.assertIsNot(app.model_executor, old_executor)

            # Wait for the original prediction to finish
            response = await predict_task
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertIn(data["prediction"]["label"], [0, 1])


if __name__ == "__main__":
    unittest.main()
