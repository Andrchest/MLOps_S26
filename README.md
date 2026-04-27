# MLOps Platform (S26)

A distributed MLOps platform supporting the full ML lifecycle: data ingestion, model training, deployment, inference serving, monitoring, and automated retraining via drift detection.

**Full architecture documentation:** [ARCHITECTURE.md](./ARCHITECTURE.md)

## Quick Start & Reproducibility

### 1. Prerequisites
* Docker & Docker Compose
* Python 3.10+
* Make

### 2. Initial Setup
Run the setup command to automatically create your local `.env` file and install Git pre-commit hooks.
```bash
make setup
```

### 3. Launch the Platform
Build and start all microservices in detached mode:
```bash
make up
```

### 4. Verify Services
Once running, services are accessible at:
* **MLflow UI:** `http://localhost:5000`
* **MinIO Console:** `http://localhost:9001` (Credentials in `.env`)
* **Orchestrator API:** `http://localhost:8000`
* **Inference API:** `http://localhost:8001`
* **Monitoring API:** `http://localhost:8002`

---

## Useful Commands
* `make logs` — Tail logs from all running Docker containers.
* `make down` — Stop and remove all containers.
* `make restart` — Tear down, rebuild, and restart the project.

---

## System Architecture & Services
The platform is built on a microservices architecture, containerized via Docker.

### Core Microservices
| Service | Port | Description |
|---------|------|-------------|
| Orchestrator | 8000 | Dataset management, training jobs, model promotion |
| Training Worker | 8500 | Polls for training jobs, executes ML pipelines |
| Inference Service | 8001 | Prediction serving with drift detection |
| Monitoring Dashboard | 8501 | Streamlit UI for system visibility |
| Monitoring Service | 8002 | Prediction logging and analysis |

### Infrastructure & Storage
| Component | Port | Description |
|-----------|------|-------------|
| PostgreSQL | 5432 | Jobs, models, deployments, prediction logs |
| MinIO | 9000/9001 | Object storage for datasets and models |
| MLflow | 5000 | Experiment tracking, model registry |
| Grafana | 3000 | Monitoring dashboards |
| Loki | 3100 | Log aggregation |

---

## Project Structure
```text
├── .github/                 # CI/CD pipelines and developer tooling
├── docs/                    # System documentation
├── experiments/             # Jupyter notebooks and EDA
├── infra/docker/            # Dockerfiles and infrastructure configs
├── pipelines/               # Data and ML pipelines
├── services/                # Source code for all microservices
├── shared/                  # Shared code/utilities across services
└── tests/                   # Pytest test suites
```

---

## Documentation

Detailed documentation, architecture decisions, and service contracts are kept in the [`docs/`](./docs) directory.

**Key Documents:**
* **[Monitoring & Logging Contract](./docs/logs_contract.md):** Specifies the required payload and database schema for logging prediction requests (Sprint 1).
* **[Drift Detection Guide](./docs/drift_detection.md):** Explains the simple drift check and retraining trigger.
* **[DVC Guide](./docs/dvc.md):** Explains the DVC pipeline and MinIO remote.
* *(More links in future)*

---

## Development Guide & Standards

We strictly enforce code quality and security standards using `pre-commit` hooks.

### Formatting & Linting
* Code is formatted using **Black** (Max line length: 88).
* Linting is handled by **Flake8**. 
* **Manual run:** `make lint`

### Commit Standards
This project follows [Conventional Commits](https://www.conventionalcommits.org/). Commit messages are automatically verified using `commitizen` on the `commit-msg` stage.
* *Example:* `feat: add new inference model` or `chore: add .dockerignore and secrets protection`

### Security & Secrets Management
We use Yelp's `detect-secrets` to prevent accidental credential leaks. The baseline of known/false-positive secrets is stored in `.secrets.baseline`.
* If you legitimately need to add a safe hash/secret, update the baseline:
  ```bash
  make update-baseline
  ```

### Testing
Run the Pytest suite via:
```bash
make test
```

---

## Demo Script

A complete end-to-end demo script is available at `scripts/demo.sh`. It demonstrates the full ML lifecycle:

```bash
# Run the entire demo
bash scripts/demo.sh all

# Or run individual steps
bash scripts/demo.sh data     # Step 1: Data ingestion
bash scripts/demo.sh train    # Step 2: Model training
bash scripts/demo.sh deploy   # Step 3: Model deployment
bash scripts/demo.sh infer    # Step 4: Inference
bash scripts/demo.sh drift    # Step 5: Drift detection & retraining
bash scripts/demo.sh fault    # Step 6: Fault tolerance (stop/restart container)
```

### What the demo shows:
1. **Data Ingestion** — Upload CSV to MinIO + PostgreSQL
2. **Training** — Create job, worker polls and executes pipeline, saves to MLflow + MinIO
3. **Deployment** — Promote trained model to production
4. **Inference** — Serve predictions with latency metrics
5. **Drift Detection** — Send out-of-distribution data, verify retraining job is auto-created
6. **Fault Tolerance** — Stop a container, verify other services continue working, restart

### Manual demo flow:
```bash
# 1. Start platform
make up

# 2. Upload dataset
curl -X POST http://localhost:8000/datasets \
  -F "file=@seeds/sample_dataset.csv" \
  -F "name=customer_churn"

# 3. Start training (replace DATASET_ID with returned id)
curl -X POST "http://localhost:8000/train?dataset_id=1&dataset_name=customer_churn"

# 4. Deploy (replace MODEL_NAME and MODEL_VERSION)
curl -X POST "http://localhost:8000/promote" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "model_name=LogisticRegression&model_version=1_1_xxx"

# 5. Make predictions
curl -X POST "http://localhost:8001/predict?model_name=LogisticRegression&model_version=1_1_xxx" \
  -H "Content-Type: application/json" \
  -d '{"age":30,"monthly_spend":100,"tenure_months":24,"income":55000,"credit_score":700}'

# 6. Trigger drift (extreme values)
curl -X POST "http://localhost:8001/predict?model_name=LogisticRegression&model_version=1_1_xxx" \
  -H "Content-Type: application/json" \
  -d '{"age":999,"monthly_spend":99999,"tenure_months":999,"income":999999,"credit_score":999}'

# 7. Fault tolerance
docker compose stop training-worker
docker compose start training-worker
```

### Access points during demo:
| Interface | URL | What to show |
|-----------|-----|-------------|
| MLflow | http://localhost:5000 | Experiment tracking, model artifacts |
| Grafana | http://localhost:3000 (admin/admin) | Real-time monitoring dashboards |
| Streamlit | http://localhost:8501 | Operational dashboard (jobs, models, deployments) |
| MinIO | http://localhost:9001 (minio/minio123) | Object storage for datasets and models |
