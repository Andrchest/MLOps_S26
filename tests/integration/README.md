# Integration Tests

This directory contains integration tests that verify the interaction between different services and the end-to-end lifecycles of the system.

## What is tested

Integration tests cover:

- **End-to-end lifecycles**: From model training to deployment and inference.
- **Service interactions**: Communication between the Orchestrator, Training Worker, Inference Service, and Monitoring Service.
- **Infrastructure integration**: Interaction with databases (PostgreSQL), object storage (MinIO), and experiment tracking (MLflow).

## Requirements

Integration tests require infrastructure components to be running.

- **Docker & Docker Compose**: Ensure `docker-compose` is installed.
- **Infrastructure Setup**: Before running tests, you must start the required services using `docker-compose`.

```bash
docker-compose up -d
```

## How to run

Run these tests from the project root using `pytest`:

```bash
pytest MLOps_S26/tests/integration
```

## Notes

- **Environment Variables**: Some tests may require specific environment variables to connect to the running infrastructure.
- **Unimplemented Features**: Tests for features that are not yet fully integrated are marked with `@pytest.mark.skip`.
- **Cleanup**: After running tests, you might want to stop the services:
  ```bash
  docker-compose down
  ```
