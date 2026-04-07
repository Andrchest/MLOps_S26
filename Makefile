.PHONY: setup update-baseline up down logs restart lint test

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
	docker-compose up --build -d

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose down
	docker-compose up --build -d

# === Code Quality & Testing ===
lint:
	pre-commit run --all-files

test:
	pytest tests/
