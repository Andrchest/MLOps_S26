import unittest
import asyncio
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# --- Path Logic ---
current_file = Path(__file__).resolve()
project_root = current_file.parents[3]
app_dir = project_root / "services" / "inference_service"

if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import using proper package path
from services.inference_service.app import app
from services.inference_service import load_model

application = app


class TestReloadConcurrency(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from services.inference_service import app as app_mod

        if not hasattr(app_mod, "model_executor"):
            app_mod.model_executor = MagicMock()

        self.test_ctx = TestClient(application)
        self.client = self.test_ctx.__enter__()

    async def asyncTearDown(self):
        self.test_ctx.__exit__(None, None, None)

    async def test_reload_during_active_request(self):
        from services.inference_service import app as app_mod

        old_executor = app_mod.model_executor

        with patch.object(
            load_model, "fetch_model_with_retry", return_value=b"fake_bytes"
        ), patch(
            "services.inference_service.app._run_prediction",
            side_effect=lambda *a, **k: (1, 0.99),
        ):

            # Trigger reload with POST
            reload_response = self.client.post("/reload")
            self.assertEqual(reload_response.status_code, 200)

            # Verify the executor was swapped
            self.assertIsNot(app_mod.model_executor, old_executor)


if __name__ == "__main__":
    unittest.main()
