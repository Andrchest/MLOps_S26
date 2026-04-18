import unittest
from unittest.mock import patch
import sys
from pathlib import Path

current_file = Path(__file__).resolve()
app_dir = current_file.parents[3] / "services" / "inference-service"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

with patch("minio_client.get_model_from_minio") as _unused_mock:
    import load_model as load_model_module

fetch_model_with_retry = load_model_module.fetch_model_with_retry


class TestFetchRetry(unittest.IsolatedAsyncioTestCase):
    @patch("load_model.get_model_from_minio")
    async def test_retry_model_fetch(self, mock_minio):
        fetch_model_with_retry.retry.wait = lambda *args, **kwargs: 0

        # fail twice then succeed
        mock_minio.side_effect = [
            Exception("fail1"),
            Exception("fail2"),
            b"model_bytes",
        ]

        result = await fetch_model_with_retry("m", "v1")

        self.assertEqual(result, b"model_bytes")
        self.assertEqual(mock_minio.call_count, 3)


if __name__ == "__main__":
    unittest.main()
