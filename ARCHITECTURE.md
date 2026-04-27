# MLOps Platform Architecture

## Overview

A distributed MLOps platform supporting the full ML lifecycle: data ingestion, model training, deployment, inference serving, monitoring, and automated retraining.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client / API Layer                       │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  POST /datasets │ POST /train  │  │  POST /promote         │ │
│  │  POST /predict   │ GET /jobs    │  │  GET /models           │ │
│  └──────┬────────┘  └──────┬───────┘  └──────────┬───────────┘ │
└─────────┼──────────────────┼─────────────────────┼─────────────┘
          │                  │                     │
          ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Orchestrator (FastAPI)                      │
│  • Dataset registration & versioning                            │
│  • Training job creation & status tracking                      │
│  • Model promotion & deployment management                      │
│  • Database: PostgreSQL (jobs, trained_models, deployments)     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Training     │  │ Inference    │  │ Monitoring   │
│ Worker       │  │ Service      │  │ Dashboard    │
│ (FastAPI)    │  │ (FastAPI)    │  │ (Streamlit)  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Shared Infrastructure                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │  MinIO   │  │  MLflow  │  │PostgreSQL│  │   Grafana    │  │
│  │(Storage) │  │(Tracking)│  │ (Database)│  │  (Monitoring)│  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Orchestrator | 8000 | Central API for dataset management, training jobs, model promotion |
| Training Worker | 8500 | Polls for training jobs, executes ML pipelines |
| Inference Service | 8001 | Serves model predictions with drift detection |
| Monitoring Dashboard | 8501 | Streamlit UI for system visibility |
| MLflow | 5000 | Experiment tracking, model registry |
| MinIO | 9000/9001 | Object storage for datasets and models |
| PostgreSQL | 5432 | Relational database for jobs, models, deployments |
| Grafana | 3000 | Monitoring dashboards |
| Loki | 3100 | Log aggregation |

## Data Flow

### 1. Data Ingestion
```
User → POST /datasets → MinIO (object storage)
              ↓
        Database (dataset_registry)
```

### 2. Model Training
```
User → POST /train → Database (jobs table, status=pending)
                              ↓
              Training Worker polls for pending jobs
                              ↓
              Downloads dataset from MinIO
                              ↓
              Runs training pipeline
                              ↓
              Logs to MLflow + saves model to MinIO
                              ↓
              Updates DB (trained_models, jobs.status=succeeded)
```

### 3. Model Deployment
```
User → POST /promote → Database (deployments table)
```

### 4. Inference
```
User → POST /predict → Inference Service
                            ↓
                    Fetch model from MinIO
                            ↓
                    Run prediction
                            ↓
                    Check drift (vs reference profile)
                            ↓
                    Log prediction to PostgreSQL
                            ↓
                    Return prediction + metadata
```

### 5. Automated Retraining (Drift Detection)
```
Prediction → Drift Analysis (vs reference profile)
                       ↓
              If drift_score > threshold:
                       ↓
              Create retraining job in DB
                       ↓
              Training Worker picks up job
                       ↓
              (Full training pipeline)
```

## Database Schema

### Tables
- **jobs** — Training job lifecycle (status: pending → running → succeeded/failed)
- **trained_models** — Model versions with metrics and parameters
- **deployments** — Active model deployments
- **prediction_logs** — Prediction history with latency and status
- **datasets** — Registered datasets with storage paths

## Key Design Decisions

### Database-Driven Job Queue
- Training jobs use PostgreSQL as a queue (no message broker needed)
- Worker uses `FOR UPDATE SKIP LOCKED` for safe concurrent job claiming
- Stuck job recovery via time-based status reset

### Model Storage
- Models stored in MinIO with path: `{model_name}/{model_version}.joblib`
- MLflow tracks experiments, parameters, metrics separately
- Inference service caches model bytes in memory

### Drift Detection
- Reference profile built from training data (mean/std per feature)
- Per-prediction drift score: `|current_value - mean| / max(std, 1)`
- Retraining triggered when drift_score exceeds threshold (default: 2.0)

### Error Handling
- MinIO retries (3 attempts) for model download
- DB connection retries on startup
- Async prediction with background drift evaluation
- Graceful degradation: inference continues if monitoring fails

## Monitoring & Observability

### Grafana Dashboards
- **ML Platform Overview**: Job counts, model counts, deployment status
- **ML Monitoring**: Predictions over time, latency trends, model usage

### Health Checks
- All services expose `/health` endpoints
- Docker-compose healthchecks with restart policies
- Correlation IDs via `asgi-correlation-id` middleware

### Logging
- Structured logging with event names
- Loki for log aggregation
- Prediction logs stored in PostgreSQL

## CI/CD Pipeline

### GitHub Actions
1. **Lint & Test** — Black, Flake8, pytest (unit + service tests)
2. **Docker Build** — Build all service images
3. **Security Scan** — Trivy vulnerability scanning

### Makefile Targets
```bash
make up              # Start all services
make test            # Run all tests
make test-unit       # Run unit tests
make test-integration # Run integration tests
make restart         # Restart all services
```

## Deployment

### Prerequisites
- Docker + Docker Compose
- Python 3.11

### Quick Start
```bash
make setup       # Create .env, install pre-commit
make up          # Start all services
make test        # Verify everything works
```

### Access Points
- Orchestrator API: http://localhost:8000
- Inference API: http://localhost:8001
- MLflow UI: http://localhost:5000
- MinIO Console: http://localhost:9001
- Grafana: http://localhost:3000 (admin/admin)
- Monitoring Dashboard: http://localhost:8501

## Assignment Requirements Coverage

| Requirement | Status | Implementation |
|------------|--------|----------------|
| Data ingestion | ✅ | CSV upload → MinIO + DB registration |
| Model versioning | ✅ | MLflow + trained_models table + MinIO |
| Automated training | ✅ | DB-driven job queue → Training Worker |
| Inference serving | ✅ | FastAPI with model caching + drift detection |
| Performance monitoring | ✅ | Grafana dashboards + prediction logs |
| Retraining triggers | ✅ | Drift detection → automatic retraining job |
| Robustness | ✅ | Health checks, retries, stuck job recovery |
| Distributed services | ✅ | 9 services via Docker Compose |
| Structured validation | ✅ | 14 integration tests + CI pipeline |
| Documentation | ✅ | This document + API endpoints |
