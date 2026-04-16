import unittest
import asyncio
import httpx
import time


# Integration test: check how many requests can be processed
# will be used later, when full system will work
class TestLoad(unittest.IsolatedAsyncioTestCase):
    async def test_high_concurrency_predictions(self):
        """Spam 100 parallel requests to test process pool stability."""
        url = "http://127.0.0.1:8000/predict?model_name=m1&model_version=v1"
        payload = {"age": 30, "monthly_spend": 100.0, "tenure_months": 5}

        async with httpx.AsyncClient() as client:
            # Create 100 concurrent POST tasks
            tasks = [client.post(url, json=payload, timeout=20.0) for _ in range(100)]

            start_time = time.perf_counter()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.perf_counter() - start_time

        successes = [
            r
            for r in responses
            if isinstance(r, httpx.Response) and r.status_code == 200
        ]
        print(
            f"\n--- Load Test: {len(successes)}/100 succeeded in {total_time:.2f}s ---"
        )

        self.assertEqual(len(successes), 100)
