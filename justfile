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
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev up --build -d

# Start development environment without nginx proxy
dev-direct:
    @echo "Starting development environment without nginx proxy..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev up --build -d api worker frontend db redis

# Start only backend services
dev-backend:
    @echo "Starting backend services only..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev up --build -d api worker db redis

# Start only frontend
dev-frontend:
    @echo "Starting frontend only..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev up --build -d frontend

# Check development environment status
dev-status:
    @echo "Development environment status:"
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev ps

# View development logs
dev-logs:
    @echo "Viewing development logs:"
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev logs

# Stop development environment
dev-stop:
    @echo "Stopping development environment..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev down

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
# Database migration commands
db-migrate:
    @echo "Running database migrations..."
    cd app/backend && alembic upgrade head

db-migrate-create:
    @echo "Creating new migration..."
    cd app/backend && alembic revision --autogenerate -m "$(message)"

db-migrate-status:
    @echo "Checking migration status..."
    cd app/backend && alembic current

db-migrate-history:
    @echo "Migration history..."
    cd app/backend && alembic history

# Market data commands
update-sp500:
    @echo "Updating S&P 500 universe..."
    curl -X POST "http://localhost:8000/v1/market-data/update-sp500-universe"

refresh-market-data:
    @echo "Refreshing market data..."
    curl -X POST "http://localhost:8000/v1/market-data/refresh-market-data"

populate-sp500-fundamentals:
    @echo "Populating SP500 fundamentals and earnings data..."
    curl -X POST "http://localhost:8000/v1/market-data/populate-sp500-fundamentals-earnings" | jq .

check-scheduled-jobs:
    @echo "Checking scheduled jobs status..."
    curl -X GET "http://localhost:8000/health/" | jq .

market-summary:
    @echo "Getting market summary..."
    curl -X GET "http://localhost:8000/v1/market-data/summary" | jq .

# Reset database (drop and recreate)
db-reset:
    @echo "Resetting database..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev down -v
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev up db -d
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
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev logs

# Show specific service logs (development)
logs-api:
    @echo "Showing API logs (development)..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev logs api

logs-worker:
    @echo "Showing worker logs (development)..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev logs worker

logs-frontend:
    @echo "Showing frontend logs (development)..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev logs frontend

logs-nginx:
    @echo "Showing nginx logs (development)..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev logs nginx

# Show production logs
logs-prod:
    @echo "Showing all production logs..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env logs

# Show specific production service logs
logs-prod-api:
    @echo "Showing API logs (production)..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env logs api

logs-prod-worker:
    @echo "Showing worker logs (production)..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env logs worker

logs-prod-frontend:
    @echo "Showing frontend logs (production)..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env logs frontend

logs-prod-nginx:
    @echo "Showing nginx logs (production)..."
    sudo docker compose -f infra/docker-compose.prod.yml --env-file .env logs nginx

# Check health of all services (development)
health:
    @echo "Checking development service health..."
    @echo "======================================"
    @echo "Nginx Health:"
    curl -s http://localhost/health | jq . | cat || echo "❌ Nginx not healthy"
    @echo ""
    @echo "API Health:"
    curl -s http://localhost:8000/health/ | jq . | cat || echo "❌ API not healthy"
    @echo ""
    @echo "API Readiness:"
    curl -s http://localhost:8000/health/ready | jq . | cat || echo "❌ API not ready"
    @echo ""
    @echo "Frontend Health:"
    curl -s http://localhost:3000 > /dev/null && echo "✅ Frontend healthy" || echo "❌ Frontend not healthy"
    @echo ""
    @echo "Recommendations Service:"
    curl -s http://localhost:8000/health/recommendations | jq . | cat || echo "❌ Recommendations service not healthy"

# Check specific service health (development)
health-nginx:
    @echo "Checking nginx health (development)..."
    curl -s http://localhost/health | jq . | cat || echo "❌ Nginx not healthy"

health-api:
    @echo "Checking API health (development)..."
    @echo "Basic health:"
    curl -s http://localhost:8000/health/ | jq . | cat || echo "❌ API not healthy"
    @echo ""
    @echo "Readiness check:"
    curl -s http://localhost:8000/health/ready | jq . | cat || echo "❌ API not ready"
    @echo ""
    @echo "Detailed health:"
    curl -s http://localhost:8000/health/detailed | jq . | cat || echo "❌ Detailed health check failed"

health-frontend:
    @echo "Checking frontend health (development)..."
    curl -s http://localhost:3000 > /dev/null && echo "✅ Frontend healthy" || echo "❌ Frontend not healthy"

health-recommendations:
    @echo "Checking recommendations service health (development)..."
    curl -s http://localhost:8000/health/recommendations | jq . | cat || echo "❌ Recommendations service not healthy"

# Check production health
health-prod:
    @echo "Checking production service health..."
    @echo "======================================"
    @echo "Nginx Health:"
    curl -s http://localhost/health | jq . | cat || echo "❌ Production nginx not healthy"
    @echo ""
    @echo "API Health:"
    curl -s http://localhost/api/health/ | jq . | cat || echo "❌ Production API not healthy (via nginx)"
    @echo ""
    @echo "Frontend Health:"
    curl -s http://localhost > /dev/null && echo "✅ Production frontend healthy" || echo "❌ Production frontend not healthy (via nginx)"

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
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev down -v
    sudo docker system prune -f

# Clear Redis cache (development)
clean-cache:
    @echo "Clearing development cache..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env.dev exec redis redis-cli FLUSHALL

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
    @echo "  dev-status             - Check development environment status"
    @echo "  dev-logs               - View development logs"
    @echo "  dev-stop               - Stop development environment"
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
    @echo "  health-recommendations - Check recommendations service health"
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
