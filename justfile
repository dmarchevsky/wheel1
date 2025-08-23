# Justfile for Wheel Strategy development

# Default target
default:
    @just --list

# Development commands
dev:
    @echo "Starting development environment..."
    cd infra && sudo docker-compose up --build

dev-backend:
    @echo "Starting backend only..."
    cd infra && sudo docker-compose up --build api worker

dev-frontend:
    @echo "Starting frontend only..."
    cd app/frontend && npm run dev

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

# Database operations
db-migrate:
    @echo "Running database migrations..."
    cd app/backend && alembic upgrade head

db-rollback:
    @echo "Rolling back database..."
    cd app/backend && alembic downgrade -1

db-reset:
    @echo "Resetting database..."
    cd infra && sudo docker compose down -v
    cd infra && sudo docker compose up db -d
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
    cd infra && sudo docker compose down -v
    sudo docker system prune -f

clean-cache:
    @echo "Cleaning cache..."
    cd infra && sudo docker compose exec redis redis-cli FLUSHALL

# Monitoring
logs:
    @echo "Showing logs..."
    cd infra && sudo docker compose logs -f

logs-api:
    @echo "Showing API logs..."
    cd infra && sudo docker compose logs -f api

logs-worker:
    @echo "Showing worker logs..."
    cd infra && sudo docker compose logs -f worker

logs-frontend:
    @echo "Showing frontend logs..."
    cd infra && sudo docker compose logs -f frontend

# Health checks
health:
    @echo "Checking service health..."
    curl -f http://localhost:8000/health || echo "API not healthy"
    curl -f http://localhost:3000 || echo "Frontend not healthy"

# Production
build:
    @echo "Building production images..."
    cd infra && sudo docker compose build

deploy:
    @echo "Deploying to production..."
    cd infra && sudo docker compose -f docker-compose.prod.yml up -d

# Help
help:
    @echo "Available commands:"
    @echo "  dev          - Start development environment"
    @echo "  test         - Run all tests"
    @echo "  lint         - Run all linters"
    @echo "  format       - Format all code"
    @echo "  db-migrate   - Run database migrations"
    @echo "  seed         - Seed database with initial data"
    @echo "  export       - Export trade data to Excel"
    @echo "  clean        - Clean up containers and volumes"
    @echo "  logs         - Show all logs"
    @echo "  health       - Check service health"
    @echo "  build        - Build production images"
    @echo "  deploy       - Deploy to production"
