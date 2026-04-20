import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
import importlib.util
import sys
from pathlib import Path

current_file = Path(__file__).resolve()
app_dir = current_file.parents[3] / "services" / "inference_service"
app_path = app_dir / "app.py"

if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))


spec = importlib.util.spec_from_file_location("app_module", str(app_path))
app_module = importlib.util.module_from_spec(spec)
sys.modules["app_module"] = app_module
spec.loader.exec_module(app_module)

application = app_module.app


class TestReload(unittest.TestCase):
    def setUp(self):
        self.mock_pool = AsyncMock()

        self.patcher = patch("asyncpg.create_pool", new_callable=AsyncMock)
        self.mock_create_pool = self.patcher.start()
        self.mock_create_pool.return_value = self.mock_pool

        self.test_ctx = TestClient(application)
        self.client = self.test_ctx.__enter__()

    def tearDown(self):
        self.test_ctx.__exit__(None, None, None)

    def test_reload_clears_cache_and_replaces_executor(self):
        app_module._MODEL_BYTES_CACHE["test_key"] = b"test_data"
        self.assertEqual(len(app_module._MODEL_BYTES_CACHE), 1)

        # Capture the reference to the original executor
        old_executor = getattr(app_module, "model_executor", None)
        self.assertIsNotNone(
            old_executor, "model_executor should be initialized by lifespan"
        )

        # Trigger reload
        response = self.client.get("/reload")

        self.assertEqual(response.status_code, 200)

        # Verify cache is now empty
        self.assertEqual(len(app_module._MODEL_BYTES_CACHE), 0)

        # Verify executor was replaced
        new_executor = app_module.model_executor
        self.assertIsNot(
            new_executor, old_executor, "Executor should be a new instance after reload"
        )


if __name__ == "__main__":
    unittest.main()
