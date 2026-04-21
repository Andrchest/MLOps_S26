import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parents[3]
app_dir = project_root / "services" / "inference_service"

# Ensure paths are set up for imports
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import using proper package path
from services.inference_service.app import app
from services.inference_service import load_model

application = app


class TestReload(unittest.TestCase):
    def setUp(self):
        from services.inference_service import app as app_mod

        if not hasattr(app_mod, "model_executor"):
            app_mod.model_executor = MagicMock()

        self.test_ctx = TestClient(application)
        self.client = self.test_ctx.__enter__()

    def tearDown(self):
        self.test_ctx.__exit__(None, None, None)

    def test_reload_clears_cache_and_replaces_executor(self):
        from services.inference_service import app as app_mod

        app_mod._MODEL_BYTES_CACHE["test_key"] = b"test_data"
        self.assertEqual(len(app_mod._MODEL_BYTES_CACHE), 1)

        old_executor = getattr(app_mod, "model_executor", None)
        self.assertIsNotNone(old_executor, "model_executor should be initialized")

        # Trigger reload with POST
        response = self.client.post("/reload")

        self.assertEqual(response.status_code, 200)

        # Verify cache is now empty
        self.assertEqual(len(app_mod._MODEL_BYTES_CACHE), 0)

        # Verify executor was replaced
        new_executor = app_mod.model_executor
        self.assertIsNot(
            new_executor, old_executor, "Executor should be a new instance after reload"
        )


if __name__ == "__main__":
    unittest.main()
