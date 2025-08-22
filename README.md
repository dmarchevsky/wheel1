# Wheel Strategy Options Assistant

A production-ready, containerized application that automates the **Wheel** options strategy with **Tradier**. The app recommends cash-secured puts, tracks positions and covered-call opportunities, notifies via Telegram with one-tap trade execution, and provides a web dashboard.

## Features

- 🤖 **Automated Recommendations**: AI-powered cash-secured put recommendations every 15 minutes during market hours
- 📱 **Telegram Integration**: One-tap trade execution with inline buttons and order previews
- 🌐 **Web Dashboard**: Real-time portfolio tracking and recommendation history
- 📊 **Advanced Scoring**: Multi-factor scoring including fundamentals, technicals, and ChatGPT analysis
- 📈 **Position Management**: Automated tracking of positions and covered-call opportunities
- 📋 **Excel Export**: Comprehensive trade and position reporting
- 🐳 **Containerized**: Full Docker deployment with health checks

## Architecture

```
/app
  /backend         # FastAPI + worker
  /frontend        # Next.js web
  /infra           # docker-compose, migrations
  /scripts         # utility scripts
```

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repo>
   cd wheel1
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Start the application**:
   ```bash
   docker compose up --build
   ```

3. **Access the application**:
   - Web Dashboard: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

4. **Setup Telegram Bot**:
   - Send `/start` to your bot
   - Use `/recs` to see current recommendations
   - Use `/positions` to view holdings

## Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Required API Keys
TRADIER_ACCESS_TOKEN=your_tradier_token
OPENAI_API_KEY=your_openai_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Database
POSTGRES_PASSWORD=secure_password
```

## Development

```bash
# Run tests
just test

# Lint code
just lint

# Seed database
just seed

# Export data
just export
```

## Trading Strategy

The Wheel Strategy involves:
1. **Selling Cash-Secured Puts**: On high-quality stocks with attractive premiums
2. **Assignment Management**: If assigned, hold the stock
3. **Covered Calls**: Sell calls against owned shares for additional income
4. **Rolling**: Adjust positions based on market conditions

## Scoring Algorithm

Recommendations are scored using:
- 35% Annualized Yield
- 20% Proximity to Support (50/200 DMA)
- 15% Liquidity Score (OI/Volume)
- 15% Risk Adjustment (earnings, sector beta)
- 15% Qualitative Score (ChatGPT analysis)

## API Endpoints

- `GET /v1/recommendations/current` - Current recommendations
- `GET /v1/positions` - Portfolio positions
- `GET /v1/portfolio` - Portfolio summary
- `POST /v1/orders/execute` - Execute trades
- `POST /v1/export/transactions.xlsx` - Export to Excel

## Telegram Commands

- `/start` - Initialize bot
- `/recs` - Show current recommendations
- `/positions` - View portfolio
- `/alerts` - Outstanding actions
- `/help` - Command help

## License

MIT License - see LICENSE file for details.
