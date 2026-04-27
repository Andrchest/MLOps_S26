.PHONY: setup update-baseline up down logs restart lint test test-unit test-integration docker-build docker-logs clean help

# === Developer Setup ===
setup:
	@echo "Creating .env file from .env.example..."
	@cp -n .env.example .env || true
	@echo "Installing pre-commit..."
	pip install pre-commit
	@echo "Installing git hooks..."
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "Setup complete! Please configure the .env file and run 'make up'."

# === Admin / Tech Lead Tools ===
update-baseline:
	@echo "Updating the secrets baseline..."
	pip install detect-secrets
	detect-secrets scan > .secrets.baseline
	@echo "Done! Please review and commit the updated .secrets.baseline file."

# === Docker Operations ===
up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

logs-service:
	docker compose logs -f --tail=100 $(service)

restart:
	docker compose down
	docker compose up --build -d

restart-service:
	docker compose up -d --build $(service)

# === Code Quality & Testing ===
lint:
	pre-commit run --all-files

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v --tb=short

test-integration:
	pytest tests/integration/ -v --tb=short

test-services:
	pytest tests/services_tests/ -v --tb=short

# === Docker Operations ===
docker-build:
	docker compose build

docker-build-service:
	docker compose build $(service)

docker-logs:
	docker compose logs -f $(service)

# === Maintenance ===
clean:
	docker compose down -v
	docker system prune -f
	@echo "Cleaned containers, volumes, and unused images"

# === Help ===
help:
	@echo "Available targets:"
	@echo "  setup              - Initial setup (env, pre-commit)"
	@echo "  up                 - Start all services"
	@echo "  down               - Stop all services"
	@echo "  restart            - Restart all services"
	@echo "  restart-service    - Restart specific service (make restart-service service=orchestrator)"
	@echo "  logs               - View all logs"
	@echo "  logs-service       - View logs for specific service (make logs-service service=orchestrator)"
	@echo "  lint               - Run pre-commit hooks"
	@echo "  test               - Run all tests"
	@echo "  test-unit          - Run unit tests"
	@echo "  test-integration   - Run integration tests"
	@echo "  test-services      - Run service tests"
	@echo "  docker-build       - Build all Docker images"
	@echo "  docker-build-service - Build specific service (make docker-build-service service=orchestrator)"
	@echo "  clean              - Clean containers, volumes, images"
	@echo "  help               - Show this help"
