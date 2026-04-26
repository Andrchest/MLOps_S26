import unittest
from unittest.mock import patch
from services.inference_service.load_model import fetch_model_with_retry


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
