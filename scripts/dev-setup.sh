#!/bin/bash

################################################################################
# Development Setup Script for Personal Finance Tracker
################################################################################
# This script provides a one-command setup for the development environment.
# It checks prerequisites, initializes configuration, and starts services.
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
SECRETS_DIR="$PROJECT_ROOT/secrets"

# Exit codes
EXIT_SUCCESS=0
EXIT_PREREQ_ERROR=1
EXIT_CONFIG_ERROR=2
EXIT_SETUP_ERROR=3

################################################################################
# Output Functions
################################################################################

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  Personal Finance Tracker - Development Setup       ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_section() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

################################################################################
# Prerequisite Checks
################################################################################

check_docker() {
    print_info "Checking Docker..."

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        echo "  Install from: https://docs.docker.com/get-docker/"
        return $EXIT_PREREQ_ERROR
    fi

    if ! docker --version &> /dev/null; then
        print_error "Docker is not responding"
        return $EXIT_PREREQ_ERROR
    fi

    print_success "Docker is installed ($(docker --version | awk '{print $3}'))"
    return $EXIT_SUCCESS
}

check_docker_compose() {
    print_info "Checking Docker Compose..."

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        echo "  Install from: https://docs.docker.com/compose/install/"
        return $EXIT_PREREQ_ERROR
    fi

    print_success "Docker Compose is installed ($(docker-compose --version | awk '{print $3}'))"
    return $EXIT_SUCCESS
}

check_node() {
    print_info "Checking Node.js..."

    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed"
        echo "  Install from: https://nodejs.org/"
        return $EXIT_PREREQ_ERROR
    fi

    print_success "Node.js is installed ($(node --version))"
    return $EXIT_SUCCESS
}

check_npm() {
    print_info "Checking npm..."

    if ! command -v npm &> /dev/null; then
        print_error "npm is not installed"
        echo "  Usually comes with Node.js"
        return $EXIT_PREREQ_ERROR
    fi

    print_success "npm is installed ($(npm --version))"
    return $EXIT_SUCCESS
}

check_python() {
    print_info "Checking Python..."

    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        echo "  Install from: https://www.python.org/"
        return $EXIT_PREREQ_ERROR
    fi

    local python_version
    python_version=$(python3 --version | awk '{print $2}')
    print_success "Python 3 is installed ($python_version)"

    # Check if version is 3.12 or higher
    local major minor
    major=$(echo "$python_version" | cut -d. -f1)
    minor=$(echo "$python_version" | cut -d. -f2)

    if [[ $major -lt 3 ]] || [[ ($major -eq 3 && $minor -lt 12) ]]; then
        print_warning "Python 3.12 or higher is recommended (found: $python_version)"
    fi

    return $EXIT_SUCCESS
}

check_poetry() {
    print_info "Checking Poetry..."

    if ! command -v poetry &> /dev/null; then
        print_warning "Poetry is not installed in PATH"
        echo "  Poetry will be installed in Docker during build"
        return $EXIT_SUCCESS
    fi

    print_success "Poetry is installed ($(poetry --version | awk '{print $1, $2}'))"
    return $EXIT_SUCCESS
}

check_prerequisites() {
    print_section "Checking Prerequisites"

    local all_ok=true

    check_docker || all_ok=false
    check_docker_compose || all_ok=false
    check_node || all_ok=false
    check_npm || all_ok=false
    check_python || all_ok=false
    check_poetry || all_ok=false

    if [[ "$all_ok" == "false" ]]; then
        print_error "Some prerequisites are missing"
        return $EXIT_PREREQ_ERROR
    fi

    print_success "All prerequisites are installed"
    return $EXIT_SUCCESS
}

################################################################################
# Configuration Setup
################################################################################

setup_env_file() {
    print_section "Setting Up Environment Variables"

    if [[ ! -f "$ENV_FILE" ]]; then
        print_info "Creating .env file from .env.example..."

        if [[ ! -f "$ENV_EXAMPLE" ]]; then
            print_error ".env.example not found"
            return $EXIT_CONFIG_ERROR
        fi

        cp "$ENV_EXAMPLE" "$ENV_FILE"
        print_success ".env file created"
        print_warning "Review .env file and update sensitive values before deploying"
    else
        print_success ".env file already exists"
    fi

    return $EXIT_SUCCESS
}

create_secrets_directory() {
    print_info "Creating secrets directory..."

    mkdir -p "$SECRETS_DIR"
    print_success "Secrets directory ready: $SECRETS_DIR"

    if [[ ! -f "$SECRETS_DIR/.gitkeep" ]]; then
        touch "$SECRETS_DIR/.gitkeep"
        print_info "Add Gmail credentials to: $SECRETS_DIR/credentials.json"
    fi

    return $EXIT_SUCCESS
}

################################################################################
# Docker Services
################################################################################

start_database() {
    print_section "Starting PostgreSQL Database"

    print_info "Starting PostgreSQL container..."

    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" up -d postgres; then
        print_error "Failed to start PostgreSQL"
        return $EXIT_SETUP_ERROR
    fi

    print_success "PostgreSQL started"

    # Wait for database to be ready
    print_info "Waiting for database to be ready..."
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres \
                pg_isready -U finance_user &> /dev/null; then
            print_success "PostgreSQL is ready"
            return $EXIT_SUCCESS
        fi
        ((attempt++))
        sleep 1
    done

    print_error "PostgreSQL did not become ready in time"
    return $EXIT_SETUP_ERROR
}

start_redis() {
    print_section "Starting Redis Cache"

    print_info "Starting Redis container..."

    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" up -d redis; then
        print_error "Failed to start Redis"
        return $EXIT_SETUP_ERROR
    fi

    print_success "Redis started"

    # Wait for redis to be ready
    print_info "Waiting for Redis to be ready..."
    local max_attempts=30
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if docker-compose -f "$DOCKER_COMPOSE_FILE" exec -T redis \
                redis-cli -a redis_password ping &> /dev/null; then
            print_success "Redis is ready"
            return $EXIT_SUCCESS
        fi
        ((attempt++))
        sleep 1
    done

    print_error "Redis did not become ready in time"
    return $EXIT_SETUP_ERROR
}

################################################################################
# Backend Setup
################################################################################

setup_backend() {
    print_section "Setting Up Backend"

    if [[ ! -d "$BACKEND_DIR" ]]; then
        print_error "Backend directory not found: $BACKEND_DIR"
        return $EXIT_SETUP_ERROR
    fi

    print_info "Installing backend dependencies with Poetry..."

    cd "$BACKEND_DIR"

    if ! poetry install; then
        print_error "Failed to install backend dependencies"
        cd "$PROJECT_ROOT"
        return $EXIT_SETUP_ERROR
    fi

    print_success "Backend dependencies installed"

    # Run migrations
    print_info "Running database migrations..."

    if ! poetry run alembic upgrade head; then
        print_error "Database migrations failed"
        cd "$PROJECT_ROOT"
        return $EXIT_SETUP_ERROR
    fi

    print_success "Database migrations completed"

    cd "$PROJECT_ROOT"
    return $EXIT_SUCCESS
}

################################################################################
# Frontend Setup
################################################################################

setup_frontend() {
    print_section "Setting Up Frontend"

    if [[ ! -d "$FRONTEND_DIR" ]]; then
        print_warning "Frontend directory not found, skipping frontend setup"
        print_info "The frontend will be built in Docker when services start"
        return $EXIT_SUCCESS
    fi

    print_info "Installing frontend dependencies with npm..."

    cd "$FRONTEND_DIR"

    if ! npm install; then
        print_error "Failed to install frontend dependencies"
        cd "$PROJECT_ROOT"
        return $EXIT_SETUP_ERROR
    fi

    print_success "Frontend dependencies installed"

    cd "$PROJECT_ROOT"
    return $EXIT_SUCCESS
}

################################################################################
# Service Startup
################################################################################

start_all_services() {
    print_section "Starting All Services"

    print_info "Starting all services with Docker Compose..."

    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" up -d; then
        print_error "Failed to start services"
        return $EXIT_SETUP_ERROR
    fi

    print_success "Services started"

    # Wait for backend to be ready
    print_info "Waiting for backend to be ready..."
    local max_attempts=60
    local attempt=1

    while [[ $attempt -le $max_attempts ]]; do
        if curl -s http://localhost:8000/health/ping &> /dev/null; then
            print_success "Backend is ready"
            return $EXIT_SUCCESS
        fi
        ((attempt++))
        sleep 1
    done

    print_warning "Backend did not respond, it may still be starting"
    return $EXIT_SUCCESS
}

################################################################################
# Service Status
################################################################################

show_service_status() {
    print_section "Service Status"

    docker-compose -f "$DOCKER_COMPOSE_FILE" ps

    return $EXIT_SUCCESS
}

################################################################################
# Final Instructions
################################################################################

print_completion_message() {
    print_section "Setup Complete!"

    echo -e "${GREEN}"
    echo "┌──────────────────────────────────────────────────────┐"
    echo "│         Personal Finance Tracker is Ready!           │"
    echo "└──────────────────────────────────────────────────────┘"
    echo -e "${NC}"

    cat << EOF

${BLUE}Services:${NC}
  • Frontend:  ${GREEN}http://localhost:3000${NC}
  • Backend:   ${GREEN}http://localhost:8000${NC}
  • Database:  ${GREEN}postgres://localhost:5432${NC}
  • Redis:     ${GREEN}redis://localhost:6379${NC}

${BLUE}Useful Commands:${NC}
  • View logs:           docker-compose logs -f
  • Stop services:       docker-compose down
  • Restart services:    docker-compose restart
  • Run migrations:      poetry run alembic upgrade head
  • Run tests:           poetry run pytest
  • Format code:         poetry run ruff check --fix app

${BLUE}Next Steps:${NC}
  1. Update .env file with your Gmail API credentials
  2. Add credentials.json to ./secrets/ directory
  3. Create a test transaction to verify the setup
  4. Check logs with: docker-compose logs -f backend

${BLUE}Documentation:${NC}
  • Backend README:  ./backend/README.md
  • API Docs:        http://localhost:8000/docs
  • System Design:   ./SYSTEM_DESIGN.md

EOF

    return $EXIT_SUCCESS
}

################################################################################
# Main Execution
################################################################################

main() {
    local exit_code=$EXIT_SUCCESS

    print_header

    # Check prerequisites
    check_prerequisites || return $EXIT_PREREQ_ERROR

    # Setup configuration
    setup_env_file || return $EXIT_CONFIG_ERROR
    create_secrets_directory || return $EXIT_CONFIG_ERROR

    # Start infrastructure services
    start_database || return $EXIT_SETUP_ERROR
    start_redis || return $EXIT_SETUP_ERROR

    # Setup backend and frontend
    setup_backend || {
        print_warning "Backend setup had issues, continuing..."
    }

    setup_frontend || {
        print_warning "Frontend setup had issues, continuing..."
    }

    # Start all services
    start_all_services || {
        print_warning "Services may still be starting, please wait a moment"
    }

    # Show status
    show_service_status

    # Print completion message
    print_completion_message

    return $EXIT_SUCCESS
}

# Run main function and capture exit code
main
exit $?
