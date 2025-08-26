# Justfile for Wheel Strategy development

# Default target
default:
    @just --list

# =============================================================================
# DEVELOPMENT COMMANDS
# =============================================================================

# Start development environment with hot-reloading
dev:
    @echo "Starting development environment with hot-reloading..."
    sudo docker compose -f infra/docker-compose.yml --env-file env.dev up --build

# Start development environment without nginx proxy
dev-direct:
    @echo "Starting development environment without nginx proxy..."
    sudo docker compose -f infra/docker-compose.yml --env-file env.dev up --build api worker frontend db redis

# Start only backend services
dev-backend:
    @echo "Starting backend services only..."
    sudo docker compose -f infra/docker-compose.yml --env-file env.dev up --build api worker db redis

# Start only frontend
dev-frontend:
    @echo "Starting frontend only..."
    sudo docker compose -f infra/docker-compose.yml --env-file env.dev up --build frontend

# =============================================================================
# PRODUCTION COMMANDS
# =============================================================================

# Build production images
build:
    @echo "Building production images..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env build

# Deploy to production
deploy:
    @echo "Deploying to production..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env up -d --build

# Start production environment (for testing)
prod:
    @echo "Starting production environment..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env up --build

# Stop production environment
prod-stop:
    @echo "Stopping production environment..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env down

# =============================================================================
# TESTING COMMANDS
# =============================================================================

# Run all tests
test:
    @echo "Running all tests..."
    just test-backend
    just test-frontend

# Run backend tests
test-backend:
    @echo "Running backend tests..."
    cd app/backend && python -m pytest tests/ -v

# Run frontend type checking
test-frontend-type:
    @echo "Running frontend type checking..."
    cd app/frontend && npm run type-check

# Test nginx proxy functionality
test-proxy:
    @echo "Testing nginx reverse proxy..."
    ./infra/test-proxy.sh

# =============================================================================
# CODE QUALITY COMMANDS
# =============================================================================

# Run all linters and formatters
lint:
    @echo "Running all linters..."
    just lint-backend
    just lint-frontend

# Lint backend code
lint-backend:
    @echo "Linting backend..."
    cd app/backend && ruff check . && black --check . && isort --check-only .

# Lint frontend code
lint-frontend:
    @echo "Linting frontend..."
    cd app/frontend && npm run lint

# Format all code
format:
    @echo "Formatting all code..."
    just format-backend
    just format-frontend

# Format backend code
format-backend:
    @echo "Formatting backend..."
    cd app/backend && ruff check . --fix && black . && isort .

# Format frontend code
format-frontend:
    @echo "Formatting frontend..."
    cd app/frontend && npx prettier --write .

# =============================================================================
# DATABASE COMMANDS
# =============================================================================

# Run database migrations
db-migrate:
    @echo "Running database migrations..."
    cd app/backend && alembic upgrade head

# Reset database (drop and recreate)
db-reset:
    @echo "Resetting database..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env down -v
    sudo docker compose -f infra/docker-compose.yml --env-file .env up db -d
    sleep 5
    just db-migrate
    just seed

# Seed database with initial data
seed:
    @echo "Seeding database..."
    cd app/backend && python scripts/seed.py

# =============================================================================
# MONITORING COMMANDS
# =============================================================================

# Show all logs (development)
logs:
    @echo "Showing all development logs..."
    sudo docker compose -f infra/docker-compose.yml --env-file env.dev logs -f

# Show specific service logs (development)
logs-api:
    @echo "Showing API logs (development)..."
    sudo docker compose -f infra/docker-compose.yml --env-file env.dev logs -f api

logs-worker:
    @echo "Showing worker logs (development)..."
    sudo docker compose -f infra/docker-compose.yml --env-file env.dev logs -f worker

logs-frontend:
    @echo "Showing frontend logs (development)..."
    sudo docker compose -f infra/docker-compose.yml --env-file env.dev logs -f frontend

logs-nginx:
    @echo "Showing nginx logs (development)..."
    sudo docker compose -f infra/docker-compose.yml --env-file env.dev logs -f nginx

# Show production logs
logs-prod:
    @echo "Showing all production logs..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env logs -f

# Show specific production service logs
logs-prod-api:
    @echo "Showing API logs (production)..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env logs -f api

logs-prod-worker:
    @echo "Showing worker logs (production)..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env logs -f worker

logs-prod-frontend:
    @echo "Showing frontend logs (production)..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env logs -f frontend

logs-prod-nginx:
    @echo "Showing nginx logs (production)..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env logs -f nginx

# Check health of all services (development)
health:
    @echo "Checking development service health..."
    curl -f http://localhost/health || echo "Nginx not healthy"
    curl -f http://localhost:8000/health || echo "API not healthy"
    curl -f http://localhost:3000 || echo "Frontend not healthy"

# Check specific service health (development)
health-nginx:
    @echo "Checking nginx health (development)..."
    curl -f http://localhost/health || echo "Nginx not healthy"

health-api:
    @echo "Checking API health (development)..."
    curl -f http://localhost/api/health || echo "API not healthy (via nginx)"

health-frontend:
    @echo "Checking frontend health (development)..."
    curl -f http://localhost || echo "Frontend not healthy (via nginx)"

# Check production health
health-prod:
    @echo "Checking production service health..."
    curl -f http://localhost/health || echo "Production nginx not healthy"
    curl -f http://localhost/api/health || echo "Production API not healthy (via nginx)"
    curl -f http://localhost || echo "Production frontend not healthy (via nginx)"

# =============================================================================
# SETUP COMMANDS
# =============================================================================

# Initial development setup
setup:
    @echo "Setting up development environment..."
    ./scripts/dev-setup.sh

# =============================================================================
# UTILITY COMMANDS
# =============================================================================

# Export trade data to Excel
export:
    @echo "Exporting data..."
    curl -X POST http://localhost:8000/v1/export/transactions.xlsx -o exports/trades_$(date +%Y%m%d_%H%M%S).xlsx

# Clean up development containers and volumes
clean:
    @echo "Cleaning up development environment..."
    sudo docker compose -f infra/docker-compose.yml --env-file env.dev down -v
    sudo docker system prune -f

# Clear Redis cache (development)
clean-cache:
    @echo "Clearing development cache..."
    sudo docker compose -f infra/docker-compose.yml --env-file env.dev exec redis redis-cli FLUSHALL

# Clean up production containers and volumes
clean-prod:
    @echo "Cleaning up production environment..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env down -v
    sudo docker system prune -f

# Clear Redis cache (production)
clean-cache-prod:
    @echo "Clearing production cache..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env exec redis redis-cli FLUSHALL

# =============================================================================
# HELP
# =============================================================================

# Show available commands
help:
    @echo "Available commands:"
    @echo ""
    @echo "SETUP:"
    @echo "  setup                  - Initial development setup"
    @echo ""
    @echo "DEVELOPMENT:"
    @echo "  dev                    - Start development environment with hot-reloading"
    @echo "  dev-direct             - Start without nginx proxy (direct access)"
    @echo "  dev-backend            - Start backend services only"
    @echo "  dev-frontend           - Start frontend only"
    @echo ""
    @echo "PRODUCTION:"
    @echo "  build                  - Build production images"
    @echo "  deploy                 - Deploy to production"
    @echo "  prod                   - Start production environment (for testing)"
    @echo "  prod-stop              - Stop production environment"
    @echo ""
    @echo "TESTING:"
    @echo "  test                   - Run all tests"
    @echo "  test-backend           - Run backend tests"
    @echo "  test-frontend-type     - Run frontend type checking"
    @echo "  test-proxy             - Test nginx reverse proxy"
    @echo ""
    @echo "CODE QUALITY:"
    @echo "  lint                   - Run all linters"
    @echo "  format                 - Format all code"
    @echo ""
    @echo "DATABASE:"
    @echo "  db-migrate             - Run database migrations"
    @echo "  db-reset               - Reset database"
    @echo "  seed                   - Seed database"
    @echo ""
    @echo "MONITORING (Development):"
    @echo "  logs                   - Show all development logs"
    @echo "  logs-{service}         - Show specific development service logs"
    @echo "  health                 - Check development services health"
    @echo "  health-{service}       - Check specific development service health"
    @echo ""
    @echo "MONITORING (Production):"
    @echo "  logs-prod              - Show all production logs"
    @echo "  logs-prod-{service}    - Show specific production service logs"
    @echo "  health-prod            - Check production services health"
    @echo ""
    @echo "UTILITIES:"
    @echo "  export                 - Export trade data"
    @echo "  clean                  - Clean up development containers"
    @echo "  clean-cache            - Clear development Redis cache"
    @echo "  clean-prod             - Clean up production containers"
    @echo "  clean-cache-prod       - Clear production Redis cache"
