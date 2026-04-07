# MLOps Platform (S26)

A platform for training and deploying ML models. It consists of microservices for orchestration, inference, monitoring, and training.

## 🛠 Technologies
- **Infrastructure:** Docker, Docker Compose
- **Databases & Storage:** PostgreSQL, MinIO
- **MLOps:** MLflow
- **CI/CD:** GitHub Actions, Pre-commit
- **Code Quality:** Python 3.10, Flake8, Black

## 🚀 Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Andrchest/MLOps_S26
   cd MLOps_S26
   ```

2. **Initial Setup:**
   Run the command below. It will create an `.env` file and set up git hooks for code quality checks.
   ```bash
   make setup
   ```

3. **Run the project:**
   ```bash
   make up
   ```

## 📋 Available Ports
- **Orchestrator:** `http://localhost:8000`
- **Inference Service:** `http://localhost:8001`
- **Monitoring Service:** `http://localhost:8002`
- **MLflow UI:** `http://localhost:5000`
- **MinIO Console:** `http://localhost:9001`

## 👨‍💻 Useful Commands (Makefile)
- `make logs` — view logs from all running containers
- `make down` — stop and remove all containers
- `make restart` — restart the project and rebuild images
- `make lint` — manually run pre-commit linters and formatters on all files

## 🔒 Commit Standards
This project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification. Commit messages are verified automatically using the `commitizen` hook.
Examples of valid commit messages: `feat: add new inference model` or `fix: resolve db connection issue`.
