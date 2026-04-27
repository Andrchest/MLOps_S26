# MLOps Platform (S26)

A comprehensive microservice-based platform for training, deploying, and monitoring Machine Learning models. 
*Cool description: TBD*.

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
* **Orchestrator (`:8000`)**: Manages and coordinates tasks between services. Depends on Postgres and MLflow. 
* **Training Worker**: Handles background model training jobs. Connects to Postgres, MLflow, and MinIO. 
* **Inference Service (`:8001`)**: Exposes the `/predict` endpoints for trained models. Fetches models via MLflow. 
* **Monitoring Service (`:8002`)**: Observes prediction requests and logs them to the database for model quality analysis.

### Infrastructure & Storage
* **PostgreSQL (`:5432`)**: Relational database for application state and prediction logs.
* **MinIO (`:9000`, console `:9001`)**: S3-compatible object storage for datasets.
* **MLflow (`:5000`)**: Model registry and experiment tracking.

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
