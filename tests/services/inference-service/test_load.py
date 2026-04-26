import unittest
import asyncio
import httpx
import time
import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

current_file = Path(__file__).resolve()
app_dir = current_file.parents[3] / "services" / "inference-service"
app_path = app_dir / "app.py"

if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

spec = importlib.util.spec_from_file_location("load_app_module", str(app_path))
app_module = importlib.util.module_from_spec(spec)
sys.modules["load_app_module"] = app_module
spec.loader.exec_module(app_module)


# Integration test: check how many requests can be processed
# will be used later, when full system will work
class TestLoad(unittest.IsolatedAsyncioTestCase):
    async def test_high_concurrency_predictions(self):
        """Run many concurrent in-process requests against the inference app."""
        payload = {"age": 30, "monthly_spend": 100.0, "tenure_months": 5}
        mock_pool = AsyncMock()
        transport = httpx.ASGITransport(app=app_module.app)

        with (
            patch.object(
                app_module.asyncpg, "create_pool", AsyncMock(return_value=mock_pool)
            ),
            patch.object(
                app_module, "fetch_model_bytes", AsyncMock(return_value=b"fake_bytes")
            ),
            patch.object(app_module, "_run_prediction", return_value=(1, 0.99)),
        ):
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                tasks = [
                    client.post(
                        "/predict?model_name=m1&model_version=v1",
                        json=payload,
                        timeout=20.0,
                    )
                    for _ in range(50)
                ]

                start_time = time.perf_counter()
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                total_time = time.perf_counter() - start_time

        successes = [
            r
            for r in responses
            if isinstance(r, httpx.Response) and r.status_code == 200
        ]
        print(
            f"\n--- Load Test: {len(successes)}/50 succeeded in {total_time:.2f}s ---"
        )

        self.assertEqual(len(successes), 50)
