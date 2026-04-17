"""MLOps Platform Integration Tests

This module contains integration tests that validate:
1. Complete ML lifecycle (§7.1 from architecture_baseline.md)
2. Distributed systems mechanisms (§7.2 from architecture_baseline.md)

## Structure

tests/integration/
├── conftest.py           # Test configuration and fixtures
├── test_full_lifecycle.py  # §7.1 Lifecycle tests
└── README.md             # This file

## Running Tests

# Run all integration tests
pytest tests/integration/ -v

# Run only lifecycle tests
pytest tests/integration/test_full_lifecycle.py -v

# Run only distributed systems tests
pytest tests/integration/test_full_lifecycle.py::TestDistributedSystemsValidation -v

# Run smoke tests only
pytest tests/integration/test_full_lifecycle.py::TestSmokeTests -v

## Test Categories

### 1. Lifecycle Validation (§7.1)
- test_dataset_ingestion: Data Ingestion and Versioning
- test_training_job_start: Training job creation
- test_training_job_completion: Job status updates
- test_model_version_registration: Model versioning
- test_model_deployment: Deployment (not yet implemented)
- test_inference_serving: Real-time predictions
- test_prediction_logging: Monitoring
- test_retraining_trigger: Auto-retraining (not yet implemented)

### 2. Distributed-Systems Validation (§7.2)
- test_idempotency_training: §5.1 Universal Idempotency
- test_crash_recovery: §5.2 Renewable Leases
- test_degraded_mode_inference: §5.4 Failure Isolation
- test_partial_failure_resilience: §5.4 Failure Isolation

### 3. Smoke Tests
Basic sanity checks to verify services are up and running.

## Requirements

Tests require:
- Docker services running (docker-compose up)
- pytest, httpx, asyncpg installed
- Database accessible on localhost:5432

## Notes

- Some tests are marked with pytest.skip() for features not yet implemented
- Tests assume services are accessible at localhost ports
- Database must have mlops user, password, and database created
"""