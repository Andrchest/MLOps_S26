# Unit Tests

This directory contains unit tests that verify the logic of individual components in isolation.

## What is tested

The unit tests cover the following modules:

- **inference_service**: Tests for the inference service logic, including prediction and loading.
- **monitoring_service**: Tests for the monitoring and metrics collection logic.
- **orchestrator**: Tests for the core orchestration logic.
- **training_worker**: Tests for the training worker processes.

## How to run

Run these tests from the project root using `pytest`:

```bash
pytest MLOps_S26/tests/unit
```

## Notes

- **Isolation**: Unit tests use mocks (via `unittest.mock` or `pytest-mock`) to ensure that components are tested without relying on databases, external services, or the file system.
- **Unimplemented Features**: Any tests for features that are still under development are marked with `@pytest.mark.skip`.
