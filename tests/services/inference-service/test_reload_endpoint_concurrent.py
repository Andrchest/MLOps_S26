import unittest
import asyncio
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
import importlib.util
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import time

current_file = Path(__file__).resolve()
app_dir = current_file.parents[3] / "services" / "inference_service"
app_path = app_dir / "app.py"

if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

# Import the module
spec = importlib.util.spec_from_file_location("app_module", str(app_path))
app_module = importlib.util.module_from_spec(spec)
sys.modules["app_module"] = app_module
spec.loader.exec_module(app_module)

application = app_module.app


class TestReloadConcurrency(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.test_ctx = TestClient(application)
        self.client = self.test_ctx.__enter__()
        app_module.model_executor = ThreadPoolExecutor(max_workers=2)

    async def asyncTearDown(self):
        app_module.model_executor.shutdown(wait=False)
        self.test_ctx.__exit__(None, None, None)

    @patch("app_module._run_prediction")
    @patch(
        "app_module.fetch_model_with_retry", new_callable=AsyncMock
    )  # Force AsyncMock
    async def test_reload_during_active_request(self, mock_fetch, mock_run):
        # Setup mocks
        mock_fetch.return_value = b"fake-model-content"

        def slow_prediction(*args, **kwargs):
            time.sleep(2)
            return 1, 0.99

        mock_run.side_effect = slow_prediction

        if not hasattr(app_module, "model_executor"):
            self.fail("model_executor not found.")

        old_executor = app_module.model_executor
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
        self.assertIsNot(app_module.model_executor, old_executor)

        # Await original task
        response = await predict_task

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["status"], "success")


if __name__ == "__main__":
    unittest.main()
