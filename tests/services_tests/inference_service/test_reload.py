import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from services.inference_service import app


class TestReload(unittest.TestCase):
    def setUp(self):
        app._MODEL_BYTES_CACHE.clear()
        self.mock_pool = AsyncMock()

        if not hasattr(app_mod, "model_executor"):
            app_mod.model_executor = MagicMock()

        self.test_ctx = TestClient(app.app)
        self.client = self.test_ctx.__enter__()

    def tearDown(self):
        self.test_ctx.__exit__(None, None, None)

    def test_reload_clears_cache_and_replaces_executor(self):
        app._MODEL_BYTES_CACHE["test_key"] = b"test_data"
        self.assertEqual(len(app._MODEL_BYTES_CACHE), 1)

        # Capture the reference to the original executor
        old_executor = getattr(app, "model_executor", None)
        self.assertIsNotNone(
            old_executor, "model_executor should be initialized by lifespan"
        )

        # Trigger reload
        response = self.client.post("/reload")

        self.assertEqual(response.status_code, 200)

        # Verify cache is now empty
        self.assertEqual(len(app._MODEL_BYTES_CACHE), 0)

        # Verify executor was replaced
        new_executor = app.model_executor
        self.assertIsNot(
            new_executor, old_executor, "Executor should be a new instance after reload"
        )


if __name__ == "__main__":
    unittest.main()
