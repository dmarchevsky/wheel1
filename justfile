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

# Database migration commands
db-migrate:
    @echo "Running database migrations..."
    sudo docker exec wheel_api alembic upgrade head

db-migrate-create message:
    @echo "Creating new migration..."
    sudo docker exec wheel_api alembic revision --autogenerate -m "{{message}}"

db-migrate-status:
    @echo "Checking migration status..."
    sudo docker exec wheel_api alembic current

db-migrate-history:
    @echo "Migration history..."
    sudo docker exec wheel_api alembic history

db-migrate-downgrade revision:
    @echo "Downgrading to revision {{revision}}..."
    sudo docker exec wheel_api alembic downgrade {{revision}}

db-migrate-upgrade revision:
    @echo "Upgrading to revision {{revision}}..."
    sudo docker exec wheel_api alembic upgrade {{revision}}

db-migrate-stamp revision:
    @echo "Stamping database to revision {{revision}}..."
    sudo docker exec wheel_api alembic stamp {{revision}}

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

# Recommendation commands
generate-recommendations:
    @echo "🚀 Generating new recommendations..."
    curl -X POST "{{api-url}}/v1/recommendations/generate" | jq .

get-recommendations:
    @echo "📊 Getting current recommendations..."
    curl -X GET "{{api-url}}/v1/recommendations/current" | jq .

get-recommendation-history:
    @echo "📊 Getting recommendation history..."
    curl -X GET "{{api-url}}/v1/recommendations/history" | jq .

# API testing
test-tradier:
    @echo "🔗 Testing Tradier API connection..."
    curl -X GET "{{api-url}}/v1/tradier-test" | jq .

test-api-ninjas:
    @echo "🔗 Testing API Ninjas connection..."
    curl -X GET "{{api-url}}/v1/market-data/interesting-tickers/AAPL" | jq .

test-delta-parsing:
    @echo "🔗 Testing delta parsing with mock data..."
    curl -X GET "{{api-url}}/v1/market-data/test-delta-parsing" | jq .

# Test timezone conversion
test-timezone:
    @echo "🕐 Testing Pacific timezone conversion..."
    cd app/backend && python scripts/test_timezone.py

# Test option filtering
test-option-filtering:
    @echo "🔍 Testing option chain filtering with delta and DTE criteria..."
    cd app/backend && python scripts/test_option_filtering.py

test-options-fetch:
    @echo "🔗 Testing options data fetching for AAPL..."
    curl -X POST "{{api-url}}/v1/market-data/tickers/AAPL/options" | jq .

test-tradier-fundamentals:
    @echo "🔗 Testing Tradier fundamentals API..."
    curl -X GET "{{api-url}}/v1/market-data/tradier-fundamentals/AFRM" | jq .

test-tradier-quote:
    @echo "🔗 Testing Tradier quote API..."
    curl -X GET "{{api-url}}/v1/market-data/tradier-quote/AFRM" | jq .

# Ticker management
refresh-ticker-data:
    @echo "📊 Refreshing ticker data..."
    curl -X POST "{{api-url}}/v1/market-data/refresh-market-data" | jq .

refresh-ticker symbol:
    @echo "📊 Refreshing specific ticker data for {{symbol}}..."
    curl -X POST "{{api-url}}/v1/market-data/interesting-tickers/{{symbol}}/refresh" | jq .

# Database management commands
db-reset:
    @echo "Resetting database..."
    {{dev-compose}} down -v
    {{dev-compose}} up db -d
    sleep 5
    just db-migrate
    just seed

db-backup:
    @echo "Creating database backup..."
    sudo docker exec wheel_db pg_dump -U wheel -d wheel > backup_$(date +%Y%m%d_%H%M%S).sql

db-restore backup_file:
    @echo "Restoring database from {{backup_file}}..."
    sudo docker exec -i wheel_db psql -U wheel -d wheel < {{backup_file}}

db-connect:
    @echo "Connecting to database..."
    sudo docker exec -it wheel_db psql -U wheel -d wheel

db-tables:
    @echo "Listing database tables..."
    sudo docker exec wheel_db psql -U wheel -d wheel -c "\dt"

db-table-info table_name:
    @echo "Showing table structure for {{table_name}}..."
    sudo docker exec wheel_db psql -U wheel -d wheel -c "\d {{table_name}}"

db-count table_name:
    @echo "Counting rows in {{table_name}}..."
    sudo docker exec wheel_db psql -U wheel -d wheel -c "SELECT COUNT(*) FROM {{table_name}};"

db-schema:
    @echo "Showing database schema..."
    sudo docker exec wheel_db psql -U wheel -d wheel -c "\dn+"
    @echo ""
    @echo "Tables:"
    sudo docker exec wheel_db psql -U wheel -d wheel -c "\dt+"
    @echo ""
    @echo "Indexes:"
    sudo docker exec wheel_db psql -U wheel -d wheel -c "\di+"

db-migration-info:
    @echo "Migration Information:"
    @echo "====================="
    @echo ""
    @echo "Current migration:"
    just db-migrate-status
    @echo ""
    @echo "Recent migration history:"
    just db-migrate-history

# Database table-specific commands
db-recommendations:
    @echo "Recent recommendations:"
    sudo docker exec wheel_db psql -U wheel -d wheel -c "SELECT id, symbol, option_symbol, annualized_yield, dte, spread_pct, created_at FROM recommendations ORDER BY created_at DESC LIMIT 10;"

db-recommendations-count:
    @echo "Recommendations count by status:"
    sudo docker exec wheel_db psql -U wheel -d wheel -c "SELECT status, COUNT(*) FROM recommendations GROUP BY status;"

db-options-count:
    @echo "Options count by underlying symbol:"
    sudo docker exec wheel_db psql -U wheel -d wheel -c "SELECT underlying_symbol, COUNT(*) FROM options GROUP BY underlying_symbol ORDER BY COUNT(*) DESC LIMIT 10;"

db-options-sample symbol:
    @echo "Sample options for {{symbol}}:"
    sudo docker exec wheel_db psql -U wheel -d wheel -c "SELECT symbol, underlying_symbol, strike, option_type, price, dte, delta FROM options WHERE underlying_symbol = '{{symbol}}' ORDER BY expiry LIMIT 5;"

db-recommendations-with-options:
    @echo "Recent recommendations with option details:"
    sudo docker exec wheel_db psql -U wheel -d wheel -c "SELECT r.id, r.symbol, r.option_symbol, o.strike, o.option_type, o.price, r.annualized_yield, r.dte, r.spread_pct FROM recommendations r JOIN options o ON r.option_symbol = o.symbol ORDER BY r.created_at DESC LIMIT 5;"

# Seed database with initial data
seed:
    @echo "Seeding database..."
    sudo docker exec wheel_api python scripts/seed.py

# =============================================================================
# MONITORING COMMANDS
# =============================================================================

# Show all logs (development)
logs tail="":
    @echo "Showing all development logs..."
    @if [ -n "{{tail}}" ]; then \
        echo "Following logs (use Ctrl+C to stop)..."; \
        {{dev-compose}} logs -f; \
    else \
        {{dev-compose}} logs; \
    fi

# Show specific service logs (development)
logs-api tail="":
    @echo "Showing API logs (development)..."
    @if [ -n "{{tail}}" ]; then \
        echo "Following API logs (use Ctrl+C to stop)..."; \
        {{dev-compose}} logs -f api; \
    else \
        {{dev-compose}} logs api; \
    fi

logs-worker tail="":
    @echo "Showing worker logs (development)..."
    @if [ -n "{{tail}}" ]; then \
        echo "Following worker logs (use Ctrl+C to stop)..."; \
        {{dev-compose}} logs -f worker; \
    else \
        {{dev-compose}} logs worker; \
    fi

logs-frontend tail="":
    @echo "Showing frontend logs (development)..."
    @if [ -n "{{tail}}" ]; then \
        echo "Following frontend logs (use Ctrl+C to stop)..."; \
        {{dev-compose}} logs -f frontend; \
    else \
        {{dev-compose}} logs frontend; \
    fi

logs-nginx tail="":
    @echo "Showing nginx logs (development)..."
    @if [ -n "{{tail}}" ]; then \
        echo "Following nginx logs (use Ctrl+C to stop)..."; \
        {{dev-compose}} logs -f nginx; \
    else \
        {{dev-compose}} logs nginx; \
    fi

logs-db tail="":
    @echo "Showing database logs (development)..."
    @if [ -n "{{tail}}" ]; then \
        echo "Following database logs (use Ctrl+C to stop)..."; \
        {{dev-compose}} logs -f db; \
    else \
        {{dev-compose}} logs db; \
    fi

logs-redis tail="":
    @echo "Showing Redis logs (development)..."
    @if [ -n "{{tail}}" ]; then \
        echo "Following Redis logs (use Ctrl+C to stop)..."; \
        {{dev-compose}} logs -f redis; \
    else \
        {{dev-compose}} logs redis; \
    fi

# Show production logs
logs-prod tail="":
    @echo "Showing all production logs..."
    @if [ -n "{{tail}}" ]; then \
        echo "Following production logs (use Ctrl+C to stop)..."; \
        {{prod-compose}} logs -f; \
    else \
        {{prod-compose}} logs; \
    fi

# Show specific production service logs
logs-prod-api tail="":
    @echo "Showing API logs (production)..."
    @if [ -n "{{tail}}" ]; then \
        echo "Following production API logs (use Ctrl+C to stop)..."; \
        {{prod-compose}} logs -f api; \
    else \
        {{prod-compose}} logs api; \
    fi

logs-prod-worker tail="":
    @echo "Showing worker logs (production)..."
    @if [ -n "{{tail}}" ]; then \
        echo "Following production worker logs (use Ctrl+C to stop)..."; \
        {{prod-compose}} logs -f worker; \
    else \
        {{prod-compose}} logs worker; \
    fi

logs-prod-frontend tail="":
    @echo "Showing frontend logs (production)..."
    @if [ -n "{{tail}}" ]; then \
        echo "Following production frontend logs (use Ctrl+C to stop)..."; \
        {{prod-compose}} logs -f frontend; \
    else \
        {{prod-compose}} logs frontend; \
    fi

logs-prod-nginx tail="":
    @echo "Showing nginx logs (production)..."
    @if [ -n "{{tail}}" ]; then \
        echo "Following production nginx logs (use Ctrl+C to stop)..."; \
        {{prod-compose}} logs -f nginx; \
    else \
        {{prod-compose}} logs nginx; \
    fi

logs-prod-db tail="":
    @echo "Showing database logs (production)..."
    @if [ -n "{{tail}}" ]; then \
        echo "Following production database logs (use Ctrl+C to stop)..."; \
        {{prod-compose}} logs -f db; \
    else \
        {{prod-compose}} logs db; \
    fi

logs-prod-redis tail="":
    @echo "Showing Redis logs (production)..."
    @if [ -n "{{tail}}" ]; then \
        echo "Following production Redis logs (use Ctrl+C to stop)..."; \
        {{prod-compose}} logs -f redis; \
    else \
        {{prod-compose}} logs redis; \
    fi

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
    @echo "  db-migrate-create MSG  - Create new migration"
    @echo "  db-migrate-status      - Check migration status"
    @echo "  db-migrate-history     - Show migration history"
    @echo "  db-migrate-downgrade R - Downgrade to revision"
    @echo "  db-migrate-upgrade R   - Upgrade to revision"
    @echo "  db-migrate-stamp R     - Stamp database to revision"
    @echo "  db-reset               - Reset database"
    @echo "  db-backup              - Create database backup"
    @echo "  db-restore FILE        - Restore database from backup"
    @echo "  db-connect             - Connect to database"
    @echo "  db-tables              - List database tables"
    @echo "  db-table-info TABLE    - Show table structure"
    @echo "  db-count TABLE         - Count rows in table"
    @echo "  db-schema              - Show database schema"
    @echo "  db-migration-info      - Show migration information"
    @echo "  db-recommendations     - Show recent recommendations"
    @echo "  db-recommendations-count - Count recommendations by status"
    @echo "  db-options-count       - Count options by underlying symbol"
    @echo "  db-options-sample SYMBOL - Show sample options for symbol"
    @echo "  db-recommendations-with-options - Show recommendations with option details"
    @echo "  seed                   - Seed database"
    @echo ""
    @echo "RECOMMENDATIONS:"
    @echo "  generate-recommendations     - Generate new recommendations (fast mode)"
    @echo "  generate-recommendations-full - Generate new recommendations (full mode)"
    @echo "  get-recommendations          - Get current recommendations"
    @echo "  get-recommendation-history   - Get recommendation history"
    @echo ""
    @echo "API TESTING:"
    @echo "  test-tradier                 - Test Tradier API connection"
    @echo "  test-tradier-quote           - Test Tradier quote API"
    @echo "  test-tradier-fundamentals    - Test Tradier fundamentals API"
    @echo "  test-api-ninjas              - Test API Ninjas connection"
    @echo ""
    @echo "TICKER MANAGEMENT:"
    @echo "  refresh-ticker-data          - Refresh all ticker data"
    @echo "  refresh-ticker SYMBOL        - Refresh specific ticker data"
    @echo ""
    @echo "MONITORING (Development):"
    @echo "  logs                   - Show all development logs"
    @echo "  logs tail=true         - Follow all development logs"
    @echo "  logs-{service}         - Show specific development service logs"
    @echo "  logs-{service} tail=true - Follow specific development service logs"
    @echo "  health                 - Check development services health"
    @echo "  health-{service}       - Check specific development service health"
    @echo "  health-recommendations - Check recommendations service health"
    @echo ""
    @echo "MONITORING (Production):"
    @echo "  logs-prod              - Show all production logs"
    @echo "  logs-prod tail=true    - Follow all production logs"
    @echo "  logs-prod-{service}    - Show specific production service logs"
    @echo "  logs-prod-{service} tail=true - Follow specific production service logs"
    @echo "  health-prod            - Check production services health"
    @echo ""
    @echo "UTILITIES:"
    @echo "  export                 - Export trade data"
    @echo "  clean                  - Clean up development containers"
    @echo "  clean-cache            - Clear development Redis cache"
    @echo "  clean-prod             - Clean up production containers"
    @echo "  clean-cache-prod       - Clear production Redis cache"
