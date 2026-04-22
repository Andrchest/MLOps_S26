import unittest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from concurrent.futures import ThreadPoolExecutor
import time
from services.inference_service import app


class TestReloadConcurrency(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_ctx = TestClient(app.app)
        self.client = self.test_ctx.__enter__()
        app.model_executor = ThreadPoolExecutor(max_workers=2)

    async def asyncTearDown(self):
        app.model_executor.shutdown(wait=False)
        self.test_ctx.__exit__(None, None, None)

    @patch("services.inference_service.app._run_prediction")
    @patch(
        "services.inference_service.app.fetch_model_with_retry", new_callable=AsyncMock
    )  # Force AsyncMock
    async def test_reload_during_active_request(self, mock_fetch, mock_run):
        # Setup mocks
        mock_fetch.return_value = b"fake-model-content"

        def slow_prediction(*args, **kwargs):
            time.sleep(2)
            return 1, 0.99

        mock_run.side_effect = slow_prediction

        if not hasattr(app, "model_executor"):
            self.fail("model_executor not found.")

        old_executor = app.model_executor
        loop = asyncio.get_running_loop()

        # Start prediction
        predict_task = loop.run_in_executor(
            None,
            lambda: self.client.post(
                "/predict",
                params={"model_name": "m1", "model_version": "v1"},
                json={"age": 30, "monthly_spend": 100.0, "tenure_months": 5},
            ),
        )

        await asyncio.sleep(0.5)  # Let it enter the executor

        # Trigger reload
        reload_response = self.client.post("/reload")
        self.assertEqual(reload_response.status_code, 200)

        # Verify swap
        self.assertIsNot(app.model_executor, old_executor)

        # Await original task
        response = await predict_task

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["status"], "success")


if __name__ == "__main__":
    unittest.main()
