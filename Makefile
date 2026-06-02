# ARC Data Factory — common tasks.
COMPOSE = docker compose -f infra/docker-compose.yml

.PHONY: up down logs migrate test lint fmt typecheck

up:            ## Start the full dev stack
	$(COMPOSE) up --build -d

down:          ## Stop the stack
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api worker

migrate:       ## Run DB migrations
	cd backend && alembic upgrade head

test:          ## Run the test suite
	cd backend && pytest

lint:
	cd backend && ruff check arc tests

fmt:
	cd backend && ruff format arc tests

typecheck:
	cd backend && mypy arc
