# Wheel Strategy Assistant - Setup Guide

## Overview

This is a production-ready, containerized Wheel Strategy options trading application that provides:

- 🤖 **AI-powered recommendations** for cash-secured puts
- 📱 **Telegram bot** with one-tap trade execution
- 🌐 **Web dashboard** for portfolio management
- 📊 **Advanced scoring** with multi-factor analysis
- 🔄 **Automated scheduling** during market hours
- 📈 **Position tracking** and alert management

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)
- API keys for:
  - Tradier (options trading)
  - OpenAI (AI analysis)
  - Telegram Bot (notifications)

### 2. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd wheel1

# Copy environment templates
cp env.example .env
cp env.example env.dev

# Edit environment files with your API keys
nano .env      # Production environment
nano env.dev   # Development environment
```

### 3. Required Environment Variables

```bash
# Required API Keys
TRADIER_ACCESS_TOKEN=your_tradier_token
TRADIER_ACCOUNT_ID=your_account_id
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# OpenAI Configuration (Optional)
OPENAI_ENABLED=false  # Set to true to enable AI analysis
OPENAI_API_KEY=your_openai_key  # Required if OPENAI_ENABLED=true

# Database (can use defaults for development)
POSTGRES_PASSWORD=secure_password
```

### 4. OpenAI Configuration

The application includes optional AI-powered analysis using OpenAI's ChatGPT. By default, this feature is **disabled** to avoid unnecessary API costs during development.

To enable AI analysis:

1. Set `OPENAI_ENABLED=true` in your `.env` file
2. Provide a valid `OPENAI_API_KEY`
3. The system will automatically use ChatGPT for:
   - Stock fundamental analysis
   - Risk assessment
   - Catalyst identification
   - Qualitative scoring

When disabled, the system uses default values for qualitative scoring components.

### 5. Start the Application

```bash
# Start all services with hot-reloading (recommended for development)
just dev

# Start without nginx proxy (direct access)
just dev-direct

# Start only backend services
just dev-backend

# Start only frontend
just dev-frontend
```

### 6. Access the Application

- **Web Dashboard**: http://localhost (via nginx proxy)
- **API Documentation**: http://localhost/api/docs (via nginx proxy)
- **Health Check**: http://localhost/health (nginx) or http://localhost/api/health (API via nginx)
- **Direct Frontend**: http://localhost:3000 (bypassing proxy)
- **Direct API**: http://localhost:8000 (bypassing proxy)

## Architecture

### Services

1. **Nginx** (Reverse Proxy) - Handles CORS and routes requests
2. **API** (FastAPI) - REST API endpoints
3. **Worker** (Background) - Scheduled jobs and Telegram bot
4. **Frontend** (Next.js) - Web dashboard
5. **Database** (PostgreSQL) - Data persistence
6. **Redis** - Caching and job queue

### Nginx Reverse Proxy

The application includes an nginx reverse proxy that:

- **Eliminates CORS issues** by proxying API requests from the frontend
- **Provides a single entry point** at `http://localhost` for the entire application
- **Routes API requests** from `/api/*` to the backend service
- **Serves the frontend** at the root path
- **Includes security headers** and rate limiting
- **Supports WebSocket connections** for Next.js development

**URL Structure:**
- Frontend: `http://localhost/` (served by nginx)
- API: `http://localhost/api/*` (proxied to backend)
- Health Check: `http://localhost/health` (nginx health endpoint)

**Development Options:**
- Use `just dev` to start with nginx proxy and hot-reloading (recommended)
- Use `just dev-direct` to start without nginx (direct access)
- Use `just dev-backend` to start only backend services
- Use `just dev-frontend` to start only frontend

**Hot Reloading:**
- Backend changes automatically restart the API server
- Frontend changes automatically refresh the browser
- No container rebuilds required for code changes

### Key Components

#### Backend (`app/backend/`)

- **`main.py`** - FastAPI application entry point
- **`worker.py`** - Background worker with scheduler
- **`config.py`** - Environment configuration
- **`db/`** - Database models and session management
- **`clients/`** - External API clients (Tradier, OpenAI)
- **`core/`** - Business logic (scoring, scheduling)
- **`services/`** - Application services
- **`routers/`** - API endpoints

#### Frontend (`app/frontend/`)

- **`app/page.tsx`** - Main dashboard
- **`components/ui/`** - Reusable UI components
- **`lib/utils.ts`** - Utility functions

#### Infrastructure (`infra/`)

- **`docker-compose.yml`** - Service orchestration
- **`Dockerfile.backend`** - Backend container
- **`Dockerfile.frontend`** - Frontend container

## Development

### Local Development

```bash
# Backend development
cd app/backend
pip install -r requirements.txt
python main.py

# Frontend development
cd app/frontend
npm install
npm run dev
```

### Testing

```bash
# Run all tests
just test

# Backend tests only
just test-backend

# Frontend tests only
just test-frontend
```

### Code Quality

```bash
# Lint code
just lint

# Format code
just format
```

### Database Operations

```bash
# Run migrations
just db-migrate

# Seed database
just seed

# Reset database
just db-reset
```

## API Endpoints

### Recommendations
- `GET /v1/recommendations/current` - Current recommendations
- `GET /v1/recommendations/history` - Historical recommendations
- `POST /v1/recommendations/{id}/dismiss` - Dismiss recommendation

### Positions
- `GET /v1/positions/` - Equity positions
- `GET /v1/positions/options` - Option positions
- `GET /v1/positions/portfolio` - Portfolio summary

### Trades
- `GET /v1/trades/history` - Trade history
- `POST /v1/orders/preview` - Preview order
- `POST /v1/orders/execute` - Execute trade

### Export
- `POST /v1/export/transactions.xlsx` - Export to Excel

## Telegram Bot Commands

- `/start` - Initialize bot
- `/recs` - View current recommendations
- `/positions` - Check portfolio
- `/alerts` - View outstanding actions
- `/help` - Show help

## Scoring Algorithm

The recommendation scoring uses a weighted composite:

1. **Annualized Yield** (35%) - Premium return on capital
2. **Proximity to Support** (20%) - Technical analysis
3. **Liquidity Score** (15%) - OI, volume, spread
4. **Risk Adjustment** (15%) - Earnings, sector risk
5. **Qualitative Score** (15%) - ChatGPT analysis

## Configuration

### Trading Parameters

```bash
# Delta range for puts
PUT_DELTA_MIN=0.25
PUT_DELTA_MAX=0.35

# IV Rank range
IVR_MIN=30
IVR_MAX=60

# Liquidity thresholds
MIN_OI=500
MIN_VOLUME=200
MAX_BID_ASK_PCT=5

# Yield requirements
ANNUALIZED_MIN_PCT=20
```

### Scheduling

```bash
# Market hours (ET)
MARKET_TIMEZONE=America/New_York

# Recommendation frequency
RECOMMENDER_INTERVAL_MIN=15
```

## Monitoring

### Health Checks

```bash
# Check service health
just health

# View logs
just logs
just logs-api
just logs-worker
```

### Metrics

- Application logs in JSON format
- Database query performance
- API response times
- Cache hit rates

## Production Deployment

### Environment

```bash
# Set production environment
ENV=prod

# Use production compose file
docker compose -f docker-compose.prod.yml up -d
```

### Security

- All secrets in environment variables
- No hardcoded credentials
- Input validation on all endpoints
- Rate limiting on API calls

### Scaling

- Horizontal scaling with load balancer
- Database connection pooling
- Redis for session storage
- CDN for static assets

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check PostgreSQL container is running
   - Verify connection string in .env

2. **API keys not working**
   - Ensure all required keys are set
   - Check API key permissions

3. **Telegram bot not responding**
   - Verify bot token and chat ID
   - Check bot has message permissions

4. **Recommendations not generating**
   - Check market hours
   - Verify Tradier API access
   - Review scoring thresholds

### Logs

```bash
# View all logs
just logs

# Filter by service
just logs-api
just logs-worker

# Follow logs
just logs
```

## Support

For issues and questions:

1. Check the logs for error messages
2. Verify environment configuration
3. Test API endpoints manually
4. Review the documentation

## License

MIT License - see LICENSE file for details.
