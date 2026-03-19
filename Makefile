.PHONY: help dev stop restart logs lint test test-backend test-frontend \
	migrate backup restore clean build build-backend build-frontend format \
	install-deps health-check run-backend run-frontend

# Configuration
COMPOSE_FILE := docker-compose.yml
DOCKER_COMPOSE := docker-compose -f $(COMPOSE_FILE)
PYTHON := poetry
NODE := npm

# Directories
BACKEND_DIR := backend
FRONTEND_DIR := frontend
SCRIPTS_DIR := scripts

# Colors for output
GREEN := \033[0;32m
BLUE := \033[0;34m
YELLOW := \033[1;33m
NC := \033[0m # No Color

################################################################################
# Default Target
################################################################################

.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "$(BLUE)Personal Finance Tracker - Development Makefile$(NC)"
	@echo ""
	@echo "$(BLUE)Usage:$(NC)"
	@echo "  make [target]"
	@echo ""
	@echo "$(BLUE)Targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

################################################################################
# Development Environment
################################################################################

setup: ## One-command dev environment setup (runs dev-setup.sh)
	@echo "$(BLUE)Running development setup...$(NC)"
	@bash $(SCRIPTS_DIR)/dev-setup.sh

dev: ## Start development environment (background)
	@echo "$(BLUE)Starting development environment...$(NC)"
	@$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✓ Development environment started$(NC)"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend:  http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

dev-foreground: ## Start development environment (foreground, logs visible)
	@echo "$(BLUE)Starting development environment...$(NC)"
	@$(DOCKER_COMPOSE) up

stop: ## Stop development environment
	@echo "$(BLUE)Stopping development environment...$(NC)"
	@$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Development environment stopped$(NC)"

restart: ## Restart development environment
	@echo "$(BLUE)Restarting development environment...$(NC)"
	@$(DOCKER_COMPOSE) restart
	@echo "$(GREEN)✓ Development environment restarted$(NC)"

logs: ## Show logs from all services (tail -f)
	@$(DOCKER_COMPOSE) logs -f

logs-backend: ## Show logs from backend service
	@$(DOCKER_COMPOSE) logs -f backend

logs-frontend: ## Show logs from frontend service
	@$(DOCKER_COMPOSE) logs -f frontend

logs-postgres: ## Show logs from PostgreSQL service
	@$(DOCKER_COMPOSE) logs -f postgres

logs-redis: ## Show logs from Redis service
	@$(DOCKER_COMPOSE) logs -f redis

health-check: ## Check health of all services
	@echo "$(BLUE)Checking service health...$(NC)"
	@echo ""
	@echo "$(BLUE)Docker Compose Status:$(NC)"
	@$(DOCKER_COMPOSE) ps
	@echo ""
	@echo "$(BLUE)Backend Health:$(NC)"
	@curl -s http://localhost:8000/health/ping && echo "$(GREEN)✓ Backend is healthy$(NC)" || echo "$(YELLOW)⚠ Backend is not responding$(NC)"
	@echo ""
	@echo "$(BLUE)Frontend Health:$(NC)"
	@curl -s http://localhost:3000 > /dev/null && echo "$(GREEN)✓ Frontend is healthy$(NC)" || echo "$(YELLOW)⚠ Frontend is not responding$(NC)"

################################################################################
# Building
################################################################################

build: build-backend build-frontend ## Build all services
	@echo "$(GREEN)✓ All services built$(NC)"

build-backend: ## Build backend service
	@echo "$(BLUE)Building backend service...$(NC)"
	@$(DOCKER_COMPOSE) build backend
	@echo "$(GREEN)✓ Backend built$(NC)"

build-frontend: ## Build frontend service
	@echo "$(BLUE)Building frontend service...$(NC)"
	@$(DOCKER_COMPOSE) build frontend
	@echo "$(GREEN)✓ Frontend built$(NC)"

rebuild: ## Rebuild all services (no cache)
	@echo "$(BLUE)Rebuilding all services...$(NC)"
	@$(DOCKER_COMPOSE) build --no-cache
	@echo "$(GREEN)✓ All services rebuilt$(NC)"

################################################################################
# Backend
################################################################################

run-backend: ## Run backend in development mode (local)
	@echo "$(BLUE)Starting backend...$(NC)"
	@cd $(BACKEND_DIR) && $(PYTHON) run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

install-backend-deps: ## Install backend dependencies (local)
	@echo "$(BLUE)Installing backend dependencies...$(NC)"
	@cd $(BACKEND_DIR) && $(PYTHON) install

test-backend: ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	@cd $(BACKEND_DIR) && $(PYTHON) run pytest -v --cov=app --cov-report=term-missing
	@echo "$(GREEN)✓ Backend tests passed$(NC)"

test-backend-quick: ## Run backend tests (quick, no coverage)
	@echo "$(BLUE)Running backend tests (quick)...$(NC)"
	@cd $(BACKEND_DIR) && $(PYTHON) run pytest -v

lint-backend: ## Lint backend code
	@echo "$(BLUE)Linting backend code...$(NC)"
	@cd $(BACKEND_DIR) && $(PYTHON) run ruff check app
	@echo "$(BLUE)Running type checking...$(NC)"
	@cd $(BACKEND_DIR) && $(PYTHON) run mypy app
	@echo "$(GREEN)✓ Backend linting passed$(NC)"

format-backend: ## Format backend code
	@echo "$(BLUE)Formatting backend code...$(NC)"
	@cd $(BACKEND_DIR) && $(PYTHON) run ruff check --fix app
	@echo "$(GREEN)✓ Backend code formatted$(NC)"

migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	@cd $(BACKEND_DIR) && $(PYTHON) run alembic upgrade head
	@echo "$(GREEN)✓ Migrations completed$(NC)"

migrate-create: ## Create a new migration (requires message argument)
	@if [ -z "$(message)" ]; then \
		echo "$(YELLOW)Usage: make migrate-create message='Description of migration'$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Creating migration...$(NC)"
	@cd $(BACKEND_DIR) && $(PYTHON) run alembic revision --autogenerate -m "$(message)"

migrate-rollback: ## Rollback last migration
	@echo "$(BLUE)Rolling back last migration...$(NC)"
	@cd $(BACKEND_DIR) && $(PYTHON) run alembic downgrade -1
	@echo "$(GREEN)✓ Migration rolled back$(NC)"

shell: ## Start Python shell in backend container
	@echo "$(BLUE)Starting Python shell...$(NC)"
	@$(DOCKER_COMPOSE) exec backend python

bash-backend: ## Open bash shell in backend container
	@$(DOCKER_COMPOSE) exec backend /bin/bash

################################################################################
# Frontend
################################################################################

run-frontend: ## Run frontend in development mode (local)
	@echo "$(BLUE)Starting frontend...$(NC)"
	@cd $(FRONTEND_DIR) && $(NODE) start

install-frontend-deps: ## Install frontend dependencies (local)
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	@cd $(FRONTEND_DIR) && $(NODE) install

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	@cd $(FRONTEND_DIR) && $(NODE) test -- --coverage --watchAll=false
	@echo "$(GREEN)✓ Frontend tests passed$(NC)"

lint-frontend: ## Lint frontend code
	@echo "$(BLUE)Linting frontend code...$(NC)"
	@cd $(FRONTEND_DIR) && $(NODE) run lint
	@echo "$(GREEN)✓ Frontend linting passed$(NC)"

format-frontend: ## Format frontend code
	@echo "$(BLUE)Formatting frontend code...$(NC)"
	@cd $(FRONTEND_DIR) && $(NODE) run format
	@echo "$(GREEN)✓ Frontend code formatted$(NC)"

bash-frontend: ## Open bash shell in frontend container
	@$(DOCKER_COMPOSE) exec frontend /bin/bash

################################################################################
# Testing & Code Quality
################################################################################

test: test-backend test-frontend ## Run all tests
	@echo "$(GREEN)✓ All tests passed$(NC)"

test-docker: ## Run backend tests inside Docker (uses real PostgreSQL)
	@echo "$(BLUE)Running backend tests in Docker with PostgreSQL...$(NC)"
	@$(DOCKER_COMPOSE) exec -e TEST_DATABASE_URL=postgresql+asyncpg://finance_user:finance_password@postgres:5432/finance_db backend python -m pytest tests/ -v --no-cov -p no:cacheprovider -o "addopts="
	@echo "$(GREEN)✓ Docker tests passed$(NC)"

test-quick: test-backend-quick ## Run quick tests (no coverage)
	@echo "$(GREEN)✓ Quick tests passed$(NC)"

lint: lint-backend lint-frontend ## Run all linters
	@echo "$(GREEN)✓ All linting passed$(NC)"

format: format-backend format-frontend ## Format all code
	@echo "$(GREEN)✓ All code formatted$(NC)"

################################################################################
# Database & Backup
################################################################################

backup: ## Create database backup
	@echo "$(BLUE)Creating database backup...$(NC)"
	@bash $(SCRIPTS_DIR)/backup.sh
	@echo "$(GREEN)✓ Backup completed$(NC)"

backup-list: ## List available backups
	@echo "$(BLUE)Available backups:$(NC)"
	@ls -lh backups/backup_*.sql.gz* 2>/dev/null || echo "No backups found"

restore: ## Restore database from latest backup
	@echo "$(BLUE)Restoring database...$(NC)"
	@bash $(SCRIPTS_DIR)/restore.sh --latest
	@echo "$(GREEN)✓ Restore completed$(NC)"

restore-file: ## Restore database from specific backup (requires file argument)
	@if [ -z "$(file)" ]; then \
		echo "$(YELLOW)Usage: make restore-file file='backup_20240315_120000.sql.gz'$(NC)"; \
		exit 1; \
	fi
	@bash $(SCRIPTS_DIR)/restore.sh --file "$(file)"

################################################################################
# Cleanup & Maintenance
################################################################################

clean: ## Remove containers, volumes, and temporary files
	@echo "$(YELLOW)Warning: This will remove all containers and volumes.$(NC)"
	@echo "$(YELLOW)Press Ctrl+C to cancel, or wait 5 seconds to continue...$(NC)"
	@sleep 5
	@echo "$(BLUE)Cleaning up...$(NC)"
	@$(DOCKER_COMPOSE) down -v
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name .DS_Store -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup completed$(NC)"

clean-docker: ## Remove all Finance Tracker containers and images
	@echo "$(BLUE)Removing Finance Tracker containers...$(NC)"
	@docker-compose down
	@docker images | grep finance-tracker | awk '{print $$3}' | xargs -r docker rmi
	@echo "$(GREEN)✓ Docker cleanup completed$(NC)"

prune-docker: ## Prune unused Docker resources (images, volumes, networks)
	@echo "$(BLUE)Pruning Docker resources...$(NC)"
	@docker image prune -f
	@docker volume prune -f
	@docker network prune -f
	@echo "$(GREEN)✓ Docker prune completed$(NC)"

################################################################################
# Production
################################################################################

prod-build: ## Build production Docker images
	@echo "$(BLUE)Building production images...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.prod.yml build
	@echo "$(GREEN)✓ Production images built$(NC)"

prod-up: ## Start production environment
	@echo "$(BLUE)Starting production environment...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.prod.yml up -d
	@echo "$(GREEN)✓ Production environment started$(NC)"

prod-down: ## Stop production environment
	@echo "$(BLUE)Stopping production environment...$(NC)"
	@$(DOCKER_COMPOSE) -f docker-compose.prod.yml down
	@echo "$(GREEN)✓ Production environment stopped$(NC)"

prod-logs: ## Show production logs
	@$(DOCKER_COMPOSE) -f docker-compose.prod.yml logs -f

################################################################################
# Utilities
################################################################################

version: ## Show version information
	@echo "$(BLUE)Version Information:$(NC)"
	@echo "Docker: $$(docker --version)"
	@echo "Docker Compose: $$(docker-compose --version)"
	@echo "Python: $$(python3 --version)"
	@echo "Node: $$(node --version)"
	@echo "npm: $$(npm --version)"

.env: ## Create .env file from .env.example
	@if [ ! -f .env ]; then \
		echo "$(BLUE)Creating .env from .env.example...$(NC)"; \
		cp .env.example .env; \
		echo "$(GREEN)✓ .env created$(NC)"; \
		echo "$(YELLOW)⚠ Review and update .env with your settings$(NC)"; \
	else \
		echo "$(YELLOW).env already exists$(NC)"; \
	fi

secrets: ## Create secrets directory structure
	@echo "$(BLUE)Creating secrets directory...$(NC)"
	@mkdir -p secrets
	@touch secrets/.gitkeep
	@echo "$(GREEN)✓ Secrets directory created$(NC)"
	@echo "$(YELLOW)Add Gmail credentials to ./secrets/credentials.json$(NC)"

################################################################################
# Documentation
################################################################################

docs: ## Open API documentation
	@echo "$(BLUE)Opening API documentation...$(NC)"
	@echo "Visit: http://localhost:8000/docs"

################################################################################
# Advanced
################################################################################

exec-backend: ## Execute command in backend container (requires cmd argument)
	@if [ -z "$(cmd)" ]; then \
		echo "$(YELLOW)Usage: make exec-backend cmd='python manage.py command'$(NC)"; \
		exit 1; \
	fi
	@$(DOCKER_COMPOSE) exec backend $(cmd)

exec-frontend: ## Execute command in frontend container (requires cmd argument)
	@if [ -z "$(cmd)" ]; then \
		echo "$(YELLOW)Usage: make exec-frontend cmd='npm run build'$(NC)"; \
		exit 1; \
	fi
	@$(DOCKER_COMPOSE) exec frontend $(cmd)

ps: ## Show running containers
	@$(DOCKER_COMPOSE) ps

inspect: ## Inspect Docker Compose configuration
	@$(DOCKER_COMPOSE) config

validate: ## Validate Docker Compose files
	@echo "$(BLUE)Validating docker-compose.yml...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) config > /dev/null && echo "$(GREEN)✓ Valid$(NC)" || echo "$(RED)✗ Invalid$(NC)"
	@echo "$(BLUE)Validating docker-compose.prod.yml...$(NC)"
	@docker-compose -f docker-compose.prod.yml config > /dev/null && echo "$(GREEN)✓ Valid$(NC)" || echo "$(RED)✗ Invalid$(NC)"
