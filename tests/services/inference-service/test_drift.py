import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

current_file = Path(__file__).resolve()
app_dir = current_file.parents[3] / "services" / "inference-service"
app_path = app_dir / "app.py"

if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))


spec = importlib.util.spec_from_file_location("app_drift_module", str(app_path))
app_module = importlib.util.module_from_spec(spec)
sys.modules["app_drift_module"] = app_module
spec.loader.exec_module(app_module)

schemas_path = app_dir / "schemas.py"
schemas_spec = importlib.util.spec_from_file_location(
    "schemas_module", str(schemas_path)
)
schemas_module = importlib.util.module_from_spec(schemas_spec)
sys.modules["schemas_module"] = schemas_module
schemas_spec.loader.exec_module(schemas_module)

InputData = schemas_module.InputData


class _AcquireContext:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def __init__(self, conn):
        self._conn = conn

    def acquire(self):
        return _AcquireContext(self._conn)


class TestDriftEvaluation(unittest.IsolatedAsyncioTestCase):
    async def test_evaluate_drift_creates_retraining_job(self):
        app_module.DRIFT_THRESHOLD = 0.1
        conn = AsyncMock()
        app_module.db_pool = _FakePool(conn)

        reference_profile = {
            "feature_names": ["age", "monthly_spend", "tenure_months"],
            "features": {
                "age": {
                    "mean": 30.0,
                    "std": 3.0,
                },
                "monthly_spend": {
                    "mean": 100.0,
                    "std": 10.0,
                },
                "tenure_months": {
                    "mean": 12.0,
                    "std": 4.0,
                },
            },
        }

        with (
            patch.object(
                app_module,
                "get_model_context",
                AsyncMock(
                    return_value={
                        "dataset_id": 7,
                        "dataset_name": "customers.csv",
                        "parameters": {"reference_profile": reference_profile},
                    }
                ),
            ),
            patch.object(
                app_module, "create_retraining_job", AsyncMock(return_value=42)
            ),
        ):
            result = await app_module.evaluate_drift(
                request_id="req-1",
                model_name="baseline",
                model_version="v1",
                input_data=InputData(
                    age=90,
                    monthly_spend=500.0,
                    tenure_months=1,
                ),
            )

        assert result is not None
        assert result["drift_detected"] is True
        assert result["retraining_job_id"] == 42
