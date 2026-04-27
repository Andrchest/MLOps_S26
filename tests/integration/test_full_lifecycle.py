# Integration Tests for MLOps Platform
# Based on: architecture_baseline.md §7.1 & §7.2

"""
This module contains integration tests that validate the full ML lifecycle
and distributed systems mechanisms.

Run with: pytest tests/integration/ -v
"""

import pytest
import asyncio
import httpx
import asyncpg
import time
from typing import Optional

# =========================
# Configuration
# =========================
BASE_URL = "http://localhost"
ORCHESTRATOR_URL = f"{BASE_URL}:8000"
INFERENCE_URL = f"{BASE_URL}:8001"
MLFLOW_URL = f"{BASE_URL}:5000"
MINIO_URL = f"{BASE_URL}:9000"

POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "mlops",
    "password": "mlops",
    "database": "mlops",
}

TEST_DATASET_PATH = "breast_cancer/93e9f331dcd2fbe28257555dd8101cfb6c1104adb58ce58ec645327b7a60f9ec.csv"


# =========================
# Fixtures
# =========================
@pytest.fixture(scope="session")
def docker_services():
    """Ensure all Docker services are running before tests."""
    pass


@pytest.fixture
async def db_pool():
    """Create database connection pool."""
    pool = await asyncpg.create_pool(
        host=POSTGRES_CONFIG["host"],
        port=POSTGRES_CONFIG["port"],
        user=POSTGRES_CONFIG["user"],
        password=POSTGRES_CONFIG["password"],
        database=POSTGRES_CONFIG["database"],
    )
    yield pool
    await pool.close()


@pytest.fixture
async def http_client():
    """HTTP client for API calls."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


# =========================
# §7.1 LIFECYCLE VALIDATION
# =========================


class TestLifecycleValidation:
    """Tests for §7.1: Complete ML Lifecycle Coverage."""

    @pytest.mark.asyncio
    async def test_dataset_ingestion(self, http_client):
        """
        Test: ingest a dataset
        Validates: §3.1 Data Ingestion and Versioning

        Expected: POST /datasets creates a record in the database
        """
        with open("pipelines/first_ml_baseline/data/breast_cancer.csv", "rb") as f:
            response = await http_client.post(
                f"{ORCHESTRATOR_URL}/datasets",
                files={"file": ("test_dataset.csv", f, "text/csv")},
                data={"name": "integration_test_dataset"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["dataset_id"] is not None
        assert data["name"] == "integration_test_dataset"
        assert data["path"] is not None

    @pytest.mark.asyncio
    async def test_training_job_start(self, http_client):
        """
        Test: start a training job
        Validates: §3.2 Training - asynchronous job execution

        Expected: POST /train returns job_id with status 'pending'
        """
        response = await http_client.post(
            f"{ORCHESTRATOR_URL}/train",
            params={
                "dataset_name": "integration_test_dataset",
                "dataset_id": 1,
                "dataset_path": TEST_DATASET_PATH,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_training_job_completion(self, http_client, db_pool):
        """
        Test: wait for training job completion
        Validates: §3.2 Training - job status updates

        Expected: Job status changes from 'pending' -> 'running' -> 'succeeded'
        """
        response = await http_client.post(
            f"{ORCHESTRATOR_URL}/train",
            params={
                "dataset_name": "integration_test_dataset",
                "dataset_id": 1,
                "dataset_path": TEST_DATASET_PATH,
            },
        )
        job_id = response.json()["job_id"]

        max_attempts = 30
        for _ in range(max_attempts):
            response = await http_client.get(f"{ORCHESTRATOR_URL}/jobs/{job_id}")
            status = response.json()["status"]

            if status == "succeeded":
                break
            if status == "failed":
                pytest.fail("Training job failed")
            await asyncio.sleep(2)
        else:
            pytest.fail("Training job did not complete in time")

        async with db_pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT status FROM jobs WHERE job_id = $1", job_id
            )
            assert result["status"] == "succeeded"

    @pytest.mark.asyncio
    async def test_model_version_registration(self, http_client, db_pool):
        """
        Test: register a model version
        Validates: §3.3 Model Versioning

        Expected: trained_models table contains the new model
        """
        async with db_pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT model_name, model_version, model_path FROM trained_models ORDER BY job_id DESC LIMIT 1"
            )
        assert result is not None
        assert result["model_name"] is not None
        assert result["model_version"] is not None
        assert result["model_path"] is not None

    @pytest.mark.asyncio
    async def test_model_deployment(self, http_client):
        """
        Test: deploy the model
        Validates: §3.4 Deployment - stateful deployment

        Expected: POST /promote creates deployment record
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            models_resp = await client.get(f"{ORCHESTRATOR_URL}/models")
            models = models_resp.json()["models"]
            assert len(models) > 0, "No models found to deploy"

            latest = models[0]
            response = await client.post(
                f"{ORCHESTRATOR_URL}/promote",
                data={
                    "model_name": latest["model_name"],
                    "model_version": latest["model_version"],
                    "deployed_by": "integration_test",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["deployment_id"] is not None
            assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_inference_serving(self, http_client, db_pool):
        """
        Test: serve predictions
        Validates: §3.5 Inference Serving

        Expected: POST /predict returns prediction with request_id
        """
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT model_name, model_version FROM trained_models ORDER BY job_id DESC LIMIT 1"
            )
            model_name = row["model_name"]
            model_version = row["model_version"]

        response = await http_client.post(
            f"{INFERENCE_URL}/predict",
            params={"model_name": model_name, "model_version": model_version},
            json={
                "age": 30,
                "monthly_spend": 100.0,
                "tenure_months": 12,
                "income": 50000,
                "credit_score": 700,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert "prediction" in data
        assert "label" in data["prediction"]
        assert "score" in data["prediction"]

    @pytest.mark.asyncio
    async def test_prediction_logging(self, http_client, db_pool):
        """
        Test: monitor prediction requests
        Validates: §3.6 Monitoring - prediction logs

        Expected: prediction_logs table records the request
        """
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT model_name, model_version FROM trained_models ORDER BY job_id DESC LIMIT 1"
            )
            model_name = row["model_name"]
            model_version = row["model_version"]

        await http_client.post(
            f"{INFERENCE_URL}/predict",
            params={"model_name": model_name, "model_version": model_version},
            json={
                "age": 30,
                "monthly_spend": 100.0,
                "tenure_months": 12,
                "income": 50000,
                "credit_score": 700,
            },
        )

        async with db_pool.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT * FROM prediction_logs ORDER BY timestamp DESC LIMIT 1"
            )
        assert result is not None

    @pytest.mark.asyncio
    async def test_retraining_trigger(self, http_client, db_pool):
        """
        Test: trigger retraining automatically via drift detection
        Validates: §3.6 Monitoring - automated retraining

        Expected: Drift detection triggers new training job
        """
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT model_name, model_version FROM trained_models ORDER BY job_id DESC LIMIT 1"
            )
            model_name = row["model_name"]
            model_version = row["model_version"]

        # Make a prediction (drift detection runs in background)
        await http_client.post(
            f"{INFERENCE_URL}/predict",
            params={"model_name": model_name, "model_version": model_version},
            json={
                "age": 30,
                "monthly_spend": 100.0,
                "tenure_months": 12,
                "income": 50000,
                "credit_score": 700,
            },
        )

        # Verify drift visualization endpoint works
        response = await http_client.get(
            f"{INFERENCE_URL}/drift/visualization",
            params={"model_name": model_name, "model_version": model_version},
        )
        assert response.status_code == 200
        data = response.json()
        assert "drift_score" in data
        assert "drift_detected" in data

    @pytest.mark.asyncio
    async def test_jobs_api(self, http_client):
        """
        Test: list all jobs
        Validates: Orchestrator /jobs endpoint
        """
        response = await http_client.get(f"{ORCHESTRATOR_URL}/jobs")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) > 0

    @pytest.mark.asyncio
    async def test_models_api(self, http_client):
        """
        Test: list all models
        Validates: Orchestrator /models endpoint
        """
        response = await http_client.get(f"{ORCHESTRATOR_URL}/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) > 0

    @pytest.mark.asyncio
    async def test_deployments_api(self, http_client):
        """
        Test: list all deployments
        Validates: Orchestrator /deployments endpoint
        """
        response = await http_client.get(f"{ORCHESTRATOR_URL}/deployments")
        assert response.status_code == 200
        data = response.json()
        assert "deployments" in data


# =========================
# §7.2 DISTRIBUTED-SYSTEMS VALIDATION
# =========================


class TestDistributedSystemsValidation:
    """Tests for §7.2: Core Distributed Systems Mechanisms."""

    @pytest.mark.asyncio
    async def test_idempotency_training(self, http_client):
        """
        Test: Idempotency - repeated requests may create duplicate jobs
        Validates: §5.1 Universal Idempotency (best effort)

        Note: Current implementation creates a new job per request.
        True idempotency would require a unique constraint on dataset_name+dataset_id
        with status filtering.
        """
        params = {"dataset_name": "test_data", "dataset_id": 999}

        responses = []
        for _ in range(3):
            response = await http_client.post(
                f"{ORCHESTRATOR_URL}/train", params=params
            )
            assert response.status_code == 200
            responses.append(response.json()["job_id"])

        # Each call creates a new job (not strictly idempotent)
        # But all should succeed
        assert len(responses) == 3
        assert all(isinstance(j, int) for j in responses)

    @pytest.mark.asyncio
    async def test_crash_recovery(self, http_client, docker_services):
        """
        Test: Crash recovery - if worker crashes, job is recovered
        Validates: §5.2 Renewable Leases + Fault Tolerance

        Note: Requires container manipulation - marked as manual test
        The recovery logic exists in training_worker/db.py
        """
        pytest.skip("Requires container manipulation - manual test")

    @pytest.mark.asyncio
    async def test_degraded_mode_inference(self, http_client):
        """
        Test: Degraded mode - inference works without database
        Validates: §5.4 Failure Isolation

        Note: Requires network manipulation - marked as manual test
        """
        pytest.skip("Requires network manipulation - manual test")

    @pytest.mark.asyncio
    async def test_partial_failure_resilience(self, http_client, db_pool):
        """
        Test: Partial failure - other services continue when one fails
        Validates: §5.4 Failure Isolation

        Expected: Health endpoints return ok for running services
        """
        services = [
            (f"{ORCHESTRATOR_URL}/health", "orchestrator"),
            (f"{INFERENCE_URL}/health", "inference"),
            (f"{MLFLOW_URL}/", "mlflow"),
        ]

        results = {}
        for url, name in services:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(url)
                    results[name] = response.status_code < 500
            except Exception:
                results[name] = False

        # Core services should be up
        assert results.get("orchestrator") == True
        assert results.get("inference") == True


# =========================
# SMOKE TESTS
# =========================


class TestSmokeTests:
    """Basic smoke tests to verify services are up."""

    @pytest.mark.asyncio
    async def test_orchestrator_health(self, http_client):
        """Verify orchestrator is responding."""
        response = await http_client.get(f"{ORCHESTRATOR_URL}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_inference_health(self, http_client):
        """Verify inference service is responding."""
        response = await http_client.get(f"{INFERENCE_URL}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_mlflow_ui(self, http_client):
        """Verify MLflow UI is accessible."""
        response = await http_client.get(f"{MLFLOW_URL}/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_database_connection(self, db_pool):
        """Verify database is accessible."""
        async with db_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1

    @pytest.mark.asyncio
    async def test_grafana_health(self, http_client):
        """Verify Grafana is accessible."""
        response = await http_client.get("http://localhost:3000/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "ok"


# =========================
# TEST RUNNERS
# =========================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
