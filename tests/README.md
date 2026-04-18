# Testing Guide

This directory contains the testing suite for the MLOps_S26 project.

## Structure

The tests are organized into two main categories:

- **unit/**: Contains unit tests for individual components, services, and modules. These tests focus on isolated functionality and use mocks to avoid external dependencies.
- **integration/**: Contains integration tests that verify the interaction between different services and the end-to-end lifecycle of the system.

## How to Run

All tests are executed using `pytest`. It is recommended to run them from the project root.

### Run all tests
```bash
pytest MLOps_S26/tests
```

### Run unit tests only
```bash
pytest MLOps_S26/tests/unit
```

### Run integration tests only
```bash
pytest MLOps_S26/tests/integration
```

## Notes

- **Unimplemented Features**: For features that are planned but not yet implemented, we use `@pytest.mark.skip` to mark the corresponding tests.
- **Environment**: Ensure your environment is set up with all necessary dependencies before running the tests.
