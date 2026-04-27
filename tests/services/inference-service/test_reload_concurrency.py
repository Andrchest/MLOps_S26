import unittest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import importlib.util
import sys
from pathlib import Path

# --- Path Logic ---
current_file = Path(__file__).resolve()
# Adjusted to find the service directory correctly
app_dir = current_file.parents[3] / "services" / "inference-service"
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
        # 1. Setup DB Mocks
        self.mock_conn = AsyncMock()
        mock_acquire_ctx = MagicMock()
        mock_acquire_ctx.__aenter__ = AsyncMock(return_value=self.mock_conn)
        mock_acquire_ctx.__aexit__ = AsyncMock(return_value=None)

        self.mock_pool = MagicMock()
        self.mock_pool.acquire.return_value = mock_acquire_ctx
        self.mock_pool.close = AsyncMock()

        # NOTE: Use "app_module" as the target because that's the name in sys.modules
        self.patcher_db = patch(
            "app_module.asyncpg.create_pool", AsyncMock(return_value=self.mock_pool)
        )
        self.patcher_fetch = patch(
            "app_module.fetch_model_bytes", AsyncMock(return_value=b"fake_bytes")
        )

        self.patcher_db.start()
        self.patcher_fetch.start()

        # This triggers the FastAPI Lifespan (Startup/Shutdown)
        self.test_ctx = TestClient(application)
        self.client = self.test_ctx.__enter__()

    async def asyncTearDown(self):
        self.test_ctx.__exit__(None, None, None)
        self.patcher_db.stop()
        self.patcher_fetch.stop()

    async def test_reload_during_active_request(self):
        # Check if model_executor exists, if not, wait a tiny bit for startup
        if not hasattr(app_module, "model_executor"):
            self.fail(
                "model_executor not found. Ensure it is initialized in the app's lifespan."
            )

        old_executor = app_module.model_executor

        # Mock the prediction to be slow
        def slow_prediction_mock(*args, **kwargs):
            import time

            time.sleep(2.0)
            return 1, 0.99

        with patch("app_module._run_prediction", side_effect=slow_prediction_mock):
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
            reload_response = self.client.get("/reload")
            self.assertEqual(reload_response.status_code, 200)

            # Verify the executor was swapped
            self.assertIsNot(app_module.model_executor, old_executor)

            # Wait for the original prediction to finish
            response = await predict_task
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertIn(data["prediction"]["label"], [0, 1])


if __name__ == "__main__":
    unittest.main()
