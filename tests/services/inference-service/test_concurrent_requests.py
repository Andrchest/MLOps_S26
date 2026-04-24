import unittest
import asyncio
import httpx
import time


# Integration test: check how many requests can be processed
# will be used later, when full system will work
class TestLoad(unittest.IsolatedAsyncioTestCase):
    async def test_high_concurrency_predictions(self):
        """Spam 100 parallel requests to test process pool stability.

        NOTE: This is an integration test that requires a running inference-service.
        Skip when running unit tests.
        """
        self.skipTest(
            "Integration test - requires running inference-service at http://127.0.0.1:8000"
        )
