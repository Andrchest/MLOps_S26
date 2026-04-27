# Monitoring Dashboard (Streamlit)

A read-only monitoring dashboard for the MLOps platform, built with Streamlit.

This dashboard provides visibility into:

- jobs
- trained models
- prediction logs
- system health
- basic monitoring metrics

---

## Purpose

The goal of this dashboard is to provide **observability into the system state** while ensuring:

- no database writes (read-only access only)
- graceful handling of failures
- support for partial and missing data
- reproducible testing via seed data

---

## Features

### System Overview

- Total jobs
- Total models
- Job status distribution
- Recent prediction logs

### Jobs

- Job list
- Job status
- Dataset association

### Models

- Trained model list
- Model version
- Model path
- Metrics
- Parameters

### Monitoring

- Total predictions
- Successful predictions
- Failed predictions
- Average latency
- Prediction status distribution
- Predictions over time (time series)
- Recent prediction logs

### System Health

- Service health checks:
  - Orchestrator
  - Inference service
  - Monitoring service

---

## Reliability & Fault Tolerance

The dashboard is designed to handle:

- Database unavailability (shows error, does not crash)
- Empty datasets (shows informative messages)
- Partial data (renders available sections only)

---

## Architecture Decisions

### Read-only Dashboard

The dashboard **never writes to the database**. It only reads from PostgreSQL and service endpoints.

### PostgreSQL as Source of Truth

The dashboard reads:

- jobs
- trained_models
- prediction_logs

MLflow is treated as an artifact store, not a state source.

### Repository Pattern

All DB queries are isolated in `repository.py`:

- keeps UI clean
- simplifies testing
- improves failure handling

### Safe Query Wrapper

All queries are executed via a safe wrapper that returns:

- success flag
- dataframe
- error message

This prevents crashes when queries fail.

### Placeholder Strategy

Some pages depend on backend contracts that are not yet finalized:

- Datasets
- Deployments

These are implemented as **explicit placeholders**, not fake data.

---

## Project Structure

```text
services/monitoring-dashboard/
├── app.py
├── db.py
├── repository.py
├── ui.py
├── requirements.txt
├── Dockerfile
├── README.md
├── test_data/
│   ├── reset.sql
│   ├── seed_basic.sql
│   └── seed_partial.sql
└── tests/
    ├── conftest.py
    ├── test_repository.py
    └── test_dashboard_integration.py
```

---

## Database Requirements

The dashboard depends on these tables:

- `jobs`
- `trained_models`
- `prediction_logs`

The `prediction_logs` table is added via shared migration:

```text
migrations/tables_for_worker.sql
```

---

## Environment Configuration

Create a `.env` file inside `services/monitoring-dashboard/`:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=55432
POSTGRES_DB=mlops
POSTGRES_USER=mlops
POSTGRES_PASSWORD=mlops
```

### Note

Port `55432` is used locally to avoid conflicts with a system PostgreSQL instance.
This is a local setup detail and should not affect the team.

---

## Running the Dashboard

From the dashboard directory:

```bash
streamlit run app.py
```

---

## Running Tests

From inside:

```bash
cd services/monitoring-dashboard
pytest
```

Includes:

- Unit tests for repository layer
- Integration test for DB-down handling

---

## Seed Data (Testing Scenarios)

The dashboard includes SQL seed files to simulate different system states.

### Reset DB

```bash
docker exec -i mlops_s26-postgres-1 psql -U mlops -d mlops < services/monitoring-dashboard/test_data/reset.sql
```

### Basic Scenario (normal system state)

```bash
docker exec -i mlops_s26-postgres-1 psql -U mlops -d mlops < services/monitoring-dashboard/test_data/seed_basic.sql
```

### Partial Scenario (missing data / failures)

```bash
docker exec -i mlops_s26-postgres-1 psql -U mlops -d mlops < services/monitoring-dashboard/test_data/seed_partial.sql
```

---

## Current Limitations

- Datasets page is a placeholder (backend contract pending)
- Deployments page is a placeholder (backend contract pending)
- Inference page is not yet implemented as a separate page
- Monitoring page does not yet include:
  - drift detection
  - model performance tracking
  - alerting system

- System Health does not yet include resource usage metrics
- Dashboard is not yet integrated into `docker-compose.yml`

---

## Future Work

- Add Datasets backend integration
- Add Deployments backend integration
- Implement Inference page
- Extend Monitoring:
  - drift detection
  - performance tracking
  - alerts

- Add resource usage to System Health
- Integrate dashboard into Docker Compose
- Align with orchestrator APIs:
  - `GET /jobs`
  - `GET /datasets`
  - `GET /models`
  - `GET /deployments`

---

## Development Notes

- `docker-compose.override.yml` is local-only and should not be committed
- `.env` is local-only and should not be committed
- Dashboard prioritizes stability over completeness (graceful failure > crash)

---

## Summary

This dashboard provides a **stable, testable, and extensible foundation** for system monitoring, with:

- real DB integration
- fault tolerance
- reproducible testing
- clear separation between implemented and pending features
