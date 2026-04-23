import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parents[2]
inference_dir = project_root / "services" / "inference_service"

# Ensure inference_service is first in sys.path
if str(inference_dir) not in sys.path:
    sys.path.insert(0, str(inference_dir))

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestFetchRetry(unittest.IsolatedAsyncioTestCase):
    @patch("services.inference_service.load_model.get_model_from_minio")
    async def test_retry_model_fetch(self, mock_minio):
        from services.inference_service import load_model

        mock_minio.side_effect = [
            Exception("fail1"),
            Exception("fail2"),
            b"model_bytes",
        ]

        result = await load_model.fetch_model_with_retry("m", "v1")

        self.assertEqual(result, b"model_bytes")
        self.assertEqual(mock_minio.call_count, 3)


if __name__ == "__main__":
    unittest.main()
