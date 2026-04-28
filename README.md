# MLOps Platform (S26)

A distributed MLOps platform supporting the full ML lifecycle: data ingestion, model training, deployment, inference serving, monitoring, and automated retraining via drift detection.

**Full architecture documentation:** [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Environment Setup](#environment-setup)
- [Services & Ports](#services--ports)
- [Documentation](#documentation)
- [Demo](#demo)
- [API Reference](#api-reference)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## Overview

The platform consists of **9 services** orchestrated via Docker Compose:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Inference   │────▶│  MinIO       │     │  PostgreSQL     │
│  Service     │     │  (9000/9001) │     │  (5432)         │
│  (8001)      │     └──────────────┘     └────────┬────────┘
└─────────────┘                                   │
       │                                          ▼
       │                                    ┌──────────┐
       │                                    │  MLflow  │
       │                                    │  (5000)  │
       │                                    └──────────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Training    │◀────│  Orchestrator│─────▶│  Monitoring     │
│  Worker      │     │  (8000)      │     │  Dashboard      │
│  (8500)      │     └──────────────┘     │  (8501)         │
└─────────────┘                           └─────────────────┘
                                               ▲
                                         ┌──────────┐
                                         │Monitoring│
                                         │ Service  │
                                         │ (8002)   │
                                         └──────────┘
```

**Key features:**
- **Automated drift detection** — inference service evaluates data drift in real-time
- **Automatic retraining** — drift triggers a new training job
- **Model versioning** — MLflow tracks experiments, metrics, and artifacts
- **Fault tolerance** — interrupted training jobs recover when worker restarts
- **Monitoring dashboard** — Streamlit UI for system visibility

---

## Quick Start

### Prerequisites

- **Docker & Docker Compose** (v2+)
- **Python 3.10+** (for local development, linting, testing)
- **Make** (for convenience commands)

### 1. Clone & Setup

```bash
cd MLOps_S26
make setup
```

This creates a `.env` file from `.env.example` and installs pre-commit hooks.

### 2. Build & Start

```bash
make up
```

Wait ~30 seconds for all services to initialize.

### 3. Verify

```bash
curl http://localhost:8000/health   # Orchestrator
curl http://localhost:8001/health   # Inference
curl http://localhost:8002/health   # Monitoring
```

All should return `{"status":"ok"}`.

### 4. Run the Demo

```bash
bash scripts/demo.sh all
```

Or run individual steps: `bash scripts/demo.sh step1`, `bash scripts/demo.sh step2`, etc.

### 5. Stop

```bash
make down
```

---

## Environment Setup

### .env File

Copy and customize:

```bash
cp .env.example .env
```

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_USER` | `mlops` | Database username |
| `POSTGRES_PASSWORD` | `mlops` | Database password |
| `POSTGRES_DB` | `mlops` | Database name |
| `POSTGRES_HOST` | `postgres` | Database hostname (Docker service name) |
| `POSTGRES_PORT` | `5432` | Database port |
| `MINIO_ROOT_USER` | `minio` | MinIO admin username |
| `MINIO_ROOT_PASSWORD` | `minio123` | MinIO admin password |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO internal endpoint |
| `MINIO_BUCKET` | `datasets` | Default MinIO bucket |
| `MLFLOW_TRACKING_URI` | `http://mlflow:5000` | MLflow tracking server |
| `ORCHESTRATOR_PORT` | `8000` | Orchestrator external port |
| `INFERENCE_PORT` | `8001` | Inference service external port |
| `MONITORING_PORT` | `8002` | Monitoring service external port |
| `WORKER_POLL_INTERVAL` | `5` | Training worker poll interval (seconds) |
| `LOG_LEVEL` | `DEBUG` | Log level for all services |
| `PYTHONUNBUFFERED` | `1` | Disable Python output buffering |

### Local Python Environment (Optional)

For local development (linting, testing, running scripts):

```bash
pip install -r services/orchestrator/requirements.txt
pip install -r services/inference_service/requirements.txt
pip install -r services/monitoring_service/requirements.txt
pip install pre-commit pytest
pre-commit install
```

---

## Services & Ports

### External Ports (Host → Container)

| Service | Port | Protocol | Description |
|---|---|---|---|
| **Orchestrator** | `8000` | HTTP | REST API (docs at `/docs`) |
| **Inference Service** | `8001` | HTTP | Prediction API (docs at `/docs`) |
| **Monitoring Service** | `8002` | HTTP | Health check, metrics API |
| **MLflow** | `5000` | HTTP | Experiment tracking UI |
| **MinIO API** | `9000` | HTTP | S3-compatible storage API |
| **MinIO Console** | `9001` | HTTP | Web UI (minio / minio123) |
| **Streamlit Dashboard** | `8501` | HTTP | Monitoring UI (admin / admin123) |
| **PostgreSQL** | `5432` | TCP | Metadata database |

> **Note:** PostgreSQL and MinIO internal ports are only accessible within the Docker network.

### Internal Service Names (Docker Compose)

Services communicate using these hostnames:

| Service | Hostname |
|---|---|
| PostgreSQL | `postgres` |
| MinIO | `minio` |
| MLflow | `mlflow` |
| Orchestrator | `orchestrator` |
| Inference | `inference_service` |
| Monitoring | `monitoring-service` |
| Training Worker | `training-worker` |

---

## Documentation

### In-Repository Documentation

| Location | Content |
|---|---|
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | Full system architecture, data flow, schema |
| [`DEMO_INSTRUCTIONS.md`](./DEMO_INSTRUCTIONS.md) | Step-by-step recording guide |
| [`docs/drift_detection.md`](./docs/drift_detection.md) | Drift detection algorithm & configuration |
| [`docs/logs_contract.md`](./docs/logs_contract.md) | Prediction logging contract & schema |
| [`services/*/README.md`](./services/) | Per-service documentation |
| [`tests/README.md`](./tests/README.md) | Testing guide |

### Live API Documentation

| Service | URL |
|---|---|
| Orchestrator | http://localhost:8000/docs |
| Inference Service | http://localhost:8001/docs |

Both use **Swagger UI** (FastAPI). Click "Try it out" to test endpoints interactively.

### Web Interfaces

| Interface | URL | Credentials |
|---|---|---|
| MLflow | http://localhost:5000 | — |
| MinIO Console | http://localhost:9001 | minio / minio123 |
| Streamlit Dashboard | http://localhost:8501 | admin / admin123 |

---

## Demo

### Automated Demo Script

```bash
# Run everything
bash scripts/demo.sh all

# Run from specific step
bash scripts/demo.sh step0    # Verify services + data ingestion
bash scripts/demo.sh step1    # Data ingestion
bash scripts/demo.sh step2    # Model training
bash scripts/demo.sh step3    # Model deployment
bash scripts/demo.sh step4    # Inference
bash scripts/demo.sh step5    # Drift detection & retraining
bash scripts/demo.sh step6    # Fault tolerance & crash recovery
```

### What Each Step Shows

| Step | Feature | What to demonstrate |
|---|---|---|
| **1** | Data Ingestion | CSV → MinIO + DB registration |
| **2** | Training | Job creation → worker execution → MLflow logging |
| **3** | Deployment | Promote model → active deployment |
| **4** | Inference | Predictions with latency metrics |
| **5** | Drift Detection | Extreme values → drift score → automatic retraining |
| **6** | Fault Tolerance | Kill worker → inference survives → crash recovery |

### Manual Demo Flow

```bash
# 1. Upload dataset
curl -X POST http://localhost:8000/datasets \
  -F "file=@seeds/sample_dataset.csv" \
  -F "name=customer_churn"

# 2. Start training
curl -X POST "http://localhost:8000/train?dataset_id=1&dataset_name=customer_churn"

# 3. Deploy (get version from trained_models)
LATEST_VER=$(docker compose exec -T postgres psql -U mlops -d mlops -t -c \
  "SELECT model_version FROM trained_models ORDER BY created_at DESC LIMIT 1;" 2>/dev/null | tr -d ' \n')

curl -X POST "http://localhost:8000/promote" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "model_name=LogisticRegression&model_version=$LATEST_VER"

# 4. Make predictions
curl -X POST "http://localhost:8001/predict?model_name=LogisticRegression&model_version=$LATEST_VER" \
  -H "Content-Type: application/json" \
  -d '{"age":30,"monthly_spend":100,"tenure_months":24,"income":55000,"credit_score":700}'

# 5. Trigger drift (extreme values)
curl -X POST "http://localhost:8001/predict?model_name=LogisticRegression&model_version=$LATEST_VER" \
  -H "Content-Type: application/json" \
  -d '{"age":999,"monthly_spend":99999,"tenure_months":999,"income":999999,"credit_score":999}'

# 6. Check drift logs
docker compose logs inference_service --tail=20 | grep drift

# 7. Fault tolerance
docker compose kill training-worker
docker compose up -d training-worker
```

---

## API Reference

### Orchestrator (Port 8000)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/datasets` | Upload dataset (multipart/form-data) |
| `GET` | `/datasets/{id}` | Get dataset info |
| `POST` | `/train` | Create training job |
| `GET` | `/jobs` | List all jobs |
| `GET` | `/jobs/{id}` | Get job status |
| `GET` | `/models` | List trained models |
| `GET` | `/deployments` | List deployments |
| `POST` | `/promote` | Promote model to production |
| `GET` | `/health` | Health check |

### Inference Service (Port 8001)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/predict` | Make prediction |
| `GET` | `/health` | Health check |

### Monitoring Service (Port 8002)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |

---

## Development

### Code Quality

```bash
make lint          # Run pre-commit hooks (Black, Flake8)
make test          # Run all tests
make test-unit     # Unit tests only
make test-integration  # Integration tests only
```

### Commit Standards

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add drift detection
fix: recover orphan training jobs
docs: update demo instructions
chore: remove obsolete files
```

### Secrets Management

```bash
make update-baseline    # Update detect-secrets baseline
```

### Docker Operations

```bash
make up                    # Build and start all services
make down                  # Stop and remove containers
make restart               # Tear down, rebuild, restart
make restart-service service=orchestrator  # Restart single service
make logs                  # Tail all logs
make logs-service service=training-worker  # Tail single service
make clean                 # Remove containers, volumes, unused images
```

---

## Troubleshooting

### Services won't start

```bash
docker compose down -v
docker compose build --no-cache
docker compose up -d
sleep 30
```

### Training fails

```bash
docker compose logs training-worker --tail=50
```

Common causes:
- Dataset not uploaded yet
- MinIO connection issue
- MLflow not ready

### Can't find model version

```bash
docker compose exec -T postgres psql -U mlops -d mlops -c \
  "SELECT model_name, model_version, created_at FROM trained_models ORDER BY created_at DESC LIMIT 5;"
```

### Drift not triggering

```bash
# Check drift detection logs
docker compose logs inference_service --tail=50 | grep -E "drift|Drift"

# Check if retraining job was created
docker compose exec -T postgres psql -U mlops -d mlops -c \
  "SELECT job_id, status, dataset_name FROM jobs ORDER BY job_id DESC LIMIT 5;"
```

### Port conflicts

If a port is already in use:
1. Update the port mapping in `.env` (e.g., `ORCHESTRATOR_PORT=8000`)
2. Update the corresponding mapping in `docker-compose.yml`
3. Restart: `make restart`

### Reset everything

```bash
make clean
make setup
make up
```

---

## Project Structure

```
├── .github/                 # CI/CD, PR templates
├── .pytest_cache/           # Test cache (gitignored)
├── docs/                    # System documentation
│   ├── drift_detection.md   # Drift detection algorithm
│   └── logs_contract.md     # Prediction logging contract
├── experiments/             # Jupyter notebooks, EDA
├── infra/                   # Dockerfiles, infrastructure configs
├── migrations/              # Database schema migrations
├── pipelines/               # ML training pipelines
│   └── first_ml_baseline/   # Baseline training pipeline
├── scripts/                 # Utility scripts
│   └── demo.sh              # End-to-end demo script
├── seeds/                   # Sample datasets
│   └── sample_dataset.csv   # Customer churn dataset
├── services/                # Microservice source code
│   ├── orchestrator/        # Dataset, job, model management
│   ├── inference_service/   # Prediction serving + drift detection
│   ├── monitoring-service/  # Monitoring API
│   ├── monitoring-dashboard/# Streamlit UI
│   ├── training_worker/     # Training job executor
│   └── mlflow/              # Custom MLflow Dockerfile
├── shared/                  # Shared utilities (logging, etc.)
├── tests/                   # Test suites
│   ├── unit/                # Component tests
│   └── integration/         # End-to-end tests
├── .env.example             # Environment template
├── .secrets.baseline        # Secrets scan baseline
├── docker-compose.yml       # Service orchestration
├── Makefile                 # Convenience commands
├── DEMO_INSTRUCTIONS.md     # Demo recording guide
├── ARCHITECTURE.md          # Full architecture docs
└── README.md                # This file
```

---

## License

This project is part of the MLOps course (S26) at [Innopolis University](https://www.innopolis.ru).
