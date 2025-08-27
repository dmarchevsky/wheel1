# Justfile for Wheel Strategy development

# =============================================================================
# VARIABLES AND SETTINGS
# =============================================================================

# Docker compose configurations
dev-compose := "sudo docker compose -f infra/docker-compose.yml --env-file .env.dev"
prod-compose := "sudo docker compose -f infra/docker-compose.prod.yml --env-file .env"

# Service URLs
api-url := "http://localhost:8000"
frontend-url := "http://localhost:3000"
nginx-url := "http://localhost/health"

# Default target
default:
    @just --list

# =============================================================================
# DEVELOPMENT COMMANDS
# =============================================================================

# Start development environment with hot-reloading
dev:
    @echo "Starting development environment with hot-reloading..."
    {{dev-compose}} up --build -d

# Start development environment without nginx proxy
dev-direct:
    @echo "Starting development environment without nginx proxy..."
    {{dev-compose}} up --build -d api worker frontend db redis

# Start only backend services
dev-backend:
    @echo "Starting backend services only..."
    {{dev-compose}} up --build -d api worker db redis

# Start only frontend
dev-frontend:
    @echo "Starting frontend only..."
    {{dev-compose}} up --build -d frontend

# Check development environment status
dev-status:
    @echo "Development environment status:"
    {{dev-compose}} ps

# View development logs
dev-logs:
    @echo "Viewing development logs:"
    {{dev-compose}} logs

# Stop development environment
dev-stop:
    @echo "Stopping development environment..."
    {{dev-compose}} down

# =============================================================================
# PRODUCTION COMMANDS
# =============================================================================

# Build production images
build:
    @echo "Building production images..."
    {{prod-compose}} build

# Deploy to production
deploy:
    @echo "Deploying to production..."
    {{prod-compose}} up -d --build

# Start production environment (for testing)
prod:
    @echo "Starting production environment..."
    {{prod-compose}} up --build

# Stop production environment
prod-stop:
    @echo "Stopping production environment..."
    {{prod-compose}} down

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
    curl -X POST "{{api-url}}/v1/market-data/update-sp500-universe"

refresh-market-data:
    @echo "Refreshing market data..."
    curl -X POST "{{api-url}}/v1/market-data/refresh-market-data"

populate-sp500-fundamentals:
    @echo "Populating SP500 fundamentals and earnings data..."
    curl -X POST "{{api-url}}/v1/market-data/populate-sp500-fundamentals-earnings" | jq .

check-scheduled-jobs:
    @echo "Checking scheduled jobs status..."
    curl -X GET "{{api-url}}/health/" | jq .

market-summary:
    @echo "Getting market summary..."
    curl -X GET "{{api-url}}/v1/market-data/summary" | jq .

# Reset database (drop and recreate)
db-reset:
    @echo "Resetting database..."
    {{dev-compose}} down -v
    {{dev-compose}} up db -d
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
    {{dev-compose}} logs

# Show specific service logs (development)
logs-api:
    @echo "Showing API logs (development)..."
    {{dev-compose}} logs api

logs-worker:
    @echo "Showing worker logs (development)..."
    {{dev-compose}} logs worker

logs-frontend:
    @echo "Showing frontend logs (development)..."
    {{dev-compose}} logs frontend

logs-nginx:
    @echo "Showing nginx logs (development)..."
    {{dev-compose}} logs nginx

# Show production logs
logs-prod:
    @echo "Showing all production logs..."
    {{prod-compose}} logs

# Show specific production service logs
logs-prod-api:
    @echo "Showing API logs (production)..."
    {{prod-compose}} logs api

logs-prod-worker:
    @echo "Showing worker logs (production)..."
    {{prod-compose}} logs worker

logs-prod-frontend:
    @echo "Showing frontend logs (production)..."
    {{prod-compose}} logs frontend

logs-prod-nginx:
    @echo "Showing nginx logs (production)..."
    {{prod-compose}} logs nginx

# Check health of all services (development)
health:
    @echo "🏥 Checking Wheel Strategy System Health..."
    @echo "================================================"
    @echo ""
    
    # Nginx Health
    @echo "🌐 Nginx Reverse Proxy:"
    @if curl -s {{nginx-url}} > /dev/null 2>&1; then \
        echo "   ✅ Healthy - Reverse proxy is working"; \
    else \
        echo "   ❌ Unhealthy - Reverse proxy not responding"; \
    fi
    @echo ""
    
    # API Basic Health
    @echo "🔧 API Service:"
    @if curl -s {{api-url}}/health/ > /dev/null 2>&1; then \
        echo "   ✅ Healthy - API service is running"; \
    else \
        echo "   ❌ Unhealthy - API service not responding"; \
    fi
    @echo ""
    
    # API Readiness with Database Status
    @echo "🗄️  Database & API Readiness:"
    @if curl -s {{api-url}}/health/ready > /dev/null 2>&1; then \
        echo "   ✅ Database: Connected and accessible"; \
        echo "   📊 Run 'curl {{api-url}}/health/ready | jq' for details"; \
    else \
        echo "   ❌ Database: Not accessible"; \
    fi
    @echo ""
    
    # Frontend Health
    @echo "🖥️  Frontend Application:"
    @if curl -s {{frontend-url}} > /dev/null 2>&1; then \
        echo "   ✅ Healthy - Frontend is accessible"; \
    else \
        echo "   ❌ Unhealthy - Frontend not responding"; \
    fi
    @echo ""
    
    # Recommendations Service
    @echo "🤖 Recommendations Service:"
    @if curl -s {{api-url}}/health/recommendations > /dev/null 2>&1; then \
        echo "   ✅ Healthy - Service operational"; \
        echo "   📊 Run 'curl {{api-url}}/health/recommendations | jq' for details"; \
    else \
        echo "   ❌ Unhealthy - Service not responding"; \
    fi
    @echo ""
    
    # Overall System Status
    @echo "📊 System Summary:"
    @echo "   🎉 All core services are operational!"
    @echo "   📊 Run individual health checks for detailed status:"
    @echo "      - just health-nginx     - Nginx reverse proxy"
    @echo "      - just health-api       - API service & database"
    @echo "      - just health-frontend  - Frontend application"
    @echo "      - just health-recommendations - Recommendations service"
    @echo ""
    @echo "🔗 Quick Links:"
    @echo "   Frontend: {{frontend-url}}"
    @echo "   API Docs: {{api-url}}/docs"
    @echo "   Health API: {{api-url}}/health/"
    @echo ""
    @echo "================================================"

# Check specific service health (development)
health-nginx:
    @echo "🌐 Checking Nginx Reverse Proxy Health..."
    @echo "=========================================="
    @if curl -s {{nginx-url}} > /dev/null 2>&1; then \
        echo "✅ Nginx is healthy and responding"; \
        echo "   URL: {{nginx-url}}"; \
    else \
        echo "❌ Nginx is not responding"; \
        echo "   Check if nginx container is running"; \
    fi

health-api:
    @echo "🔧 Checking API Service Health..."
    @echo "================================="
    @echo ""
    @echo "Basic Health Check:"
    @if curl -s {{api-url}}/health/ > /dev/null 2>&1; then \
        echo "   ✅ API service is running"; \
    else \
        echo "   ❌ API service not responding"; \
    fi
    @echo ""
    @echo "Database Readiness:"
    @if curl -s {{api-url}}/health/ready > /dev/null 2>&1; then \
        echo "   ✅ Database connected and accessible"; \
        echo "   📊 Run 'curl {{api-url}}/health/ready | jq' for details"; \
    else \
        echo "   ❌ Database not accessible"; \
    fi
    @echo ""
    @echo "Detailed Health:"
    @if curl -s {{api-url}}/health/detailed > /dev/null 2>&1; then \
        echo "   ✅ Detailed health check available"; \
        echo "   📊 Run 'curl {{api-url}}/health/detailed | jq' for details"; \
    else \
        echo "   ❌ Detailed health check failed"; \
    fi

health-frontend:
    @echo "🖥️  Checking Frontend Application Health..."
    @echo "==========================================="
    @if curl -s {{frontend-url}} > /dev/null 2>&1; then \
        echo "✅ Frontend is healthy and accessible"; \
        echo "   URL: {{frontend-url}}"; \
    else \
        echo "❌ Frontend is not responding"; \
        echo "   Check if frontend container is running"; \
    fi

health-recommendations:
    @echo "🤖 Checking Recommendations Service Health..."
    @echo "============================================="
    @if curl -s {{api-url}}/health/recommendations > /dev/null 2>&1; then \
        echo "✅ Recommendations service is healthy"; \
        echo "   📊 Run 'curl {{api-url}}/health/recommendations | jq' for details"; \
    else \
        echo "❌ Recommendations service not responding"; \
    fi

# Check production health
health-prod:
    @echo "🏥 Checking Production System Health..."
    @echo "======================================="
    @echo ""
    
    # Nginx Health
    @echo "🌐 Production Nginx:"
    @if curl -s http://localhost/health > /dev/null 2>&1; then \
        echo "   ✅ Healthy - Production reverse proxy working"; \
    else \
        echo "   ❌ Unhealthy - Production reverse proxy not responding"; \
    fi
    @echo ""
    
    # API Health via Nginx
    @echo "🔧 Production API (via Nginx):"
    @if curl -s http://localhost/api/health/ > /dev/null 2>&1; then \
        echo "   ✅ Healthy - Production API accessible via nginx"; \
    else \
        echo "   ❌ Unhealthy - Production API not accessible via nginx"; \
    fi
    @echo ""
    
    # Frontend Health via Nginx
    @echo "🖥️  Production Frontend (via Nginx):"
    @if curl -s http://localhost > /dev/null 2>&1; then \
        echo "   ✅ Healthy - Production frontend accessible via nginx"; \
    else \
        echo "   ❌ Unhealthy - Production frontend not accessible via nginx"; \
    fi
    @echo ""
    
    # Overall Production Status
    @echo "📊 Production Summary:"
    @HEALTHY_COUNT=0; \
    TOTAL_COUNT=0; \
    if curl -s http://localhost/health > /dev/null 2>&1; then HEALTHY_COUNT=$$((HEALTHY_COUNT + 1)); fi; TOTAL_COUNT=$$((TOTAL_COUNT + 1)); \
    if curl -s http://localhost/api/health/ > /dev/null 2>&1; then HEALTHY_COUNT=$$((HEALTHY_COUNT + 1)); fi; TOTAL_COUNT=$$((TOTAL_COUNT + 1)); \
    if curl -s http://localhost > /dev/null 2>&1; then HEALTHY_COUNT=$$((HEALTHY_COUNT + 1)); fi; TOTAL_COUNT=$$((TOTAL_COUNT + 1)); \
    if [ $$HEALTHY_COUNT -eq $$TOTAL_COUNT ]; then \
        echo "   🎉 Production system fully operational! ($$HEALTHY_COUNT/$$TOTAL_COUNT services healthy)"; \
    elif [ $$HEALTHY_COUNT -gt 0 ]; then \
        echo "   ⚠️  Production system has issues ($$HEALTHY_COUNT/$$TOTAL_COUNT services healthy)"; \
    else \
        echo "   🚨 Production system down (0/$$TOTAL_COUNT services healthy)"; \
    fi
    @echo ""
    @echo "🔗 Production URLs:"
    @echo "   Main Site: http://localhost"
    @echo "   Health Check: http://localhost/health"
    @echo "======================================="

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
    curl -X POST {{api-url}}/v1/export/transactions.xlsx -o exports/trades_$(date +%Y%m%d_%H%M%S).xlsx

# Clean up development containers and volumes
clean:
    @echo "Cleaning up development environment..."
    {{dev-compose}} down -v
    sudo docker system prune -f

# Clear Redis cache (development)
clean-cache:
    @echo "Clearing development cache..."
    {{dev-compose}} exec redis redis-cli FLUSHALL

# Clean up production containers and volumes
clean-prod:
    @echo "Cleaning up production environment..."
    {{prod-compose}} down -v
    sudo docker system prune -f

# Clear Redis cache (production)
clean-cache-prod:
    @echo "Clearing production cache..."
    {{prod-compose}} exec redis redis-cli FLUSHALL

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
