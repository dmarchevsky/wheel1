# Justfile for Wheel Strategy development

# Default target
default:
    @just --list

# Development commands
dev:
    @echo "Starting development environment..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env up --build

start:
    @echo "Starting the complete application..."
    just dev

start-frontend:
    @echo "Starting frontend with dependencies..."
    just dev-frontend-install
    just dev-frontend



rebuild-frontend:
    @echo "Rebuilding frontend Docker image..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env build --no-cache frontend

dev-backend:
    @echo "Starting backend only..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env up --build api worker

dev-frontend:
    @echo "Starting frontend only..."
    cd app/frontend && npm run dev

dev-frontend-docker:
    @echo "Starting frontend in Docker..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env up --build frontend

dev-frontend-install:
    @echo "Installing frontend dependencies..."
    cd app/frontend && npm install

dev-frontend-install-docker:
    @echo "Installing frontend dependencies in Docker..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env run --rm frontend npm install

# Testing
test:
    @echo "Running tests..."
    cd app/backend && python -m pytest tests/ -v

test-backend:
    @echo "Running backend tests..."
    cd app/backend && python -m pytest tests/ -v

test-frontend:
    @echo "Running frontend tests..."
    cd app/frontend && npm test

test-frontend-type:
    @echo "Running frontend type checking..."
    cd app/frontend && npm run type-check

# Linting and formatting
lint:
    @echo "Running linters..."
    just lint-backend
    just lint-frontend

lint-backend:
    @echo "Linting backend..."
    cd app/backend && ruff check . && black --check . && isort --check-only .

lint-frontend:
    @echo "Linting frontend..."
    cd app/frontend && npm run lint

format:
    @echo "Formatting code..."
    just format-backend
    just format-frontend

format-backend:
    @echo "Formatting backend..."
    cd app/backend && ruff check . --fix && black . && isort .

format-frontend:
    @echo "Formatting frontend..."
    cd app/frontend && npm run format

format-frontend-prettier:
    @echo "Formatting frontend with Prettier..."
    cd app/frontend && npx prettier --write .

# Database operations
db-migrate:
    @echo "Running database migrations..."
    cd app/backend && alembic upgrade head

db-rollback:
    @echo "Rolling back database..."
    cd app/backend && alembic downgrade -1

db-reset:
    @echo "Resetting database..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env down -v
    sudo docker compose -f infra/docker-compose.yml --env-file .env up db -d
    sleep 5
    just db-migrate
    just seed

# Seeding data
seed:
    @echo "Seeding database..."
    cd app/backend && python scripts/seed.py

# Export data
export:
    @echo "Exporting data..."
    curl -X POST http://localhost:8000/v1/export/transactions.xlsx -o exports/trades_$(date +%Y%m%d_%H%M%S).xlsx

# Cleanup
clean:
    @echo "Cleaning up..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env down -v
    sudo docker system prune -f

clean-cache:
    @echo "Cleaning cache..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env exec redis redis-cli FLUSHALL

# Monitoring
logs:
    @echo "Showing logs..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env logs -f

logs-api:
    @echo "Showing API logs..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env logs -f api

logs-worker:
    @echo "Showing worker logs..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env logs -f worker

logs-frontend:
    @echo "Showing frontend logs..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env logs -f frontend

# Health checks
health:
    @echo "Checking service health..."
    curl -f http://localhost:8000/health || echo "API not healthy"
    curl -f http://localhost:3000 || echo "Frontend not healthy"

health-frontend:
    @echo "Checking frontend health..."
    curl -f http://localhost:3000 || echo "Frontend not healthy"

health-api:
    @echo "Checking API health..."
    curl -f http://localhost:8000/health || echo "API not healthy"

# Production
build:
    @echo "Building production images..."
    sudo docker compose -f infra/docker-compose.yml --env-file .env build

deploy:
    @echo "Deploying to production..."
    sudo docker compose -f infra/docker-compose.prod.yml up -d

# Help
help:
    @echo "Available commands:"
    @echo "  dev                    - Start development environment"
    @echo "  dev-frontend           - Start frontend development server"
    @echo "  dev-frontend-docker    - Start frontend in Docker"
    @echo "  dev-frontend-install   - Install frontend dependencies"
    @echo "  rebuild-frontend       - Rebuild frontend Docker image"
    @echo "  test                   - Run all tests"
    @echo "  test-frontend-type     - Run frontend type checking"
    @echo "  lint                   - Run all linters"
    @echo "  format                 - Format all code"
    @echo "  format-frontend-prettier - Format frontend with Prettier"
    @echo "  db-migrate             - Run database migrations"
    @echo "  seed                   - Seed database with initial data"
    @echo "  export                 - Export trade data to Excel"
    @echo "  clean                  - Clean up containers and volumes"
    @echo "  logs                   - Show all logs"
    @echo "  health                 - Check service health"
    @echo "  health-frontend        - Check frontend health"
    @echo "  health-api             - Check API health"
    @echo "  build                  - Build production images"
    @echo "  deploy                 - Deploy to production"
