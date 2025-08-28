# Wheel Strategy API Documentation

## Overview

The Wheel Strategy API is a FastAPI-based service for automated options trading using the Wheel Strategy. It provides endpoints for market data management, recommendation generation, position tracking, trade execution, and data export.

**Base URL**: `http://localhost:8000`  
**API Version**: v1  
**Documentation**: Available at `/docs` (Swagger UI)

## Authentication

Currently, the API does not implement authentication. All endpoints are publicly accessible.

## API Endpoints

### Health & Status

#### `GET /health/`
Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-28T23:32:59.589607",
  "service": "wheel-strategy-api"
}
```

#### `GET /health/ready`
Readiness check with database connectivity and core services.

**Response:**
```json
{
  "status": "ready",
  "database": {
    "status": "connected",
    "tables": {
      "recommendations": {"count": 5, "status": "accessible"},
      "tickers": {"count": 506, "status": "accessible"},
      "options": {"count": 1250, "status": "accessible"}
    }
  },
  "timestamp": "2025-08-28T23:32:59.589607"
}
```

#### `GET /health/live`
Liveness check for container orchestration.

**Response:**
```json
{
  "status": "alive",
  "timestamp": "2025-08-28T23:32:59.589607"
}
```

#### `GET /health/detailed`
Detailed health check including all services and components.

### Market Data

#### `POST /v1/market-data/update-sp500-universe`
Manually trigger S&P 500 universe update.

**Response:**
```json
{
  "message": "S&P 500 universe update completed",
  "status": "success",
  "updated_tickers_count": 506,
  "timestamp": "2025-08-28T23:32:59.589607",
  "tickers": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "sector": "Technology",
      "market_cap": 2500000000000,
      "source": "sp500",
      "active": true
    }
  ]
}
```

#### `POST /v1/market-data/refresh-market-data`
Manually trigger market data refresh for active tickers.

**Response:**
```json
{
  "message": "Market data refresh completed",
  "status": "success",
  "refreshed_tickers_count": 506,
  "timestamp": "2025-08-28T23:32:59.589607",
  "tickers": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "updated_at": "2025-08-28T23:32:59.589607"
    }
  ]
}
```

#### `GET /v1/market-data/summary`
Get market data summary.

**Response:**
```json
{
  "status": "success",
  "data": {
    "total_tickers": 506,
    "active_tickers": 506,
    "last_updated": "2025-08-28T23:32:59.589607",
    "sector_distribution": {
      "Technology": 75,
      "Healthcare": 65,
      "Financial": 60
    }
  },
  "timestamp": "2025-08-28T23:32:59.589607"
}
```

#### `GET /v1/market-data/interesting-tickers`
Get list of interesting tickers for analysis.

**Query Parameters:**
- `limit` (int, optional): Number of tickers to return (default: 50, max: 100)
- `sector` (str, optional): Filter by sector
- `active_only` (bool, optional): Return only active tickers (default: true)

**Response:**
```json
{
  "tickers": [
    {
      "symbol": "AAPL",
      "name": "Apple Inc.",
      "sector": "Technology",
      "market_cap": 2500000000000,
      "current_price": 150.25,
      "active": true
    }
  ],
  "total_count": 506,
  "timestamp": "2025-08-28T23:32:59.589607"
}
```

#### `POST /v1/market-data/tickers/{symbol}/options`
Fetch options data for a specific ticker.

**Path Parameters:**
- `symbol` (str): Stock symbol (e.g., "AAPL")

**Response:**
```json
{
  "symbol": "AAPL",
  "options": [
    {
      "symbol": "AAPL",
      "expiry": "2025-09-19",
      "strike": 150.0,
      "option_type": "put",
      "bid": 2.50,
      "ask": 2.55,
      "last": 2.52,
      "delta": -0.45,
      "gamma": 0.02,
      "theta": -0.15,
      "vega": 0.25,
      "implied_volatility": 0.25,
      "open_interest": 1250,
      "volume": 500,
      "dte": 22
    }
  ],
  "count": 50,
  "timestamp": "2025-08-28T23:32:59.589607"
}
```

#### `GET /v1/market-data/test-delta-parsing`
Test endpoint for options delta parsing (development/debugging).

**Response:**
```json
{
  "message": "Delta parsing test completed",
  "parsed_options": [
    {
      "symbol": "AAPL",
      "strike": 150.0,
      "delta": -0.45,
      "gamma": 0.02,
      "theta": -0.15,
      "vega": 0.25
    }
  ],
  "timestamp": "2025-08-28T23:32:59.589607"
}
```

### Recommendations

#### `POST /v1/recommendations/generate`
Generate new trade recommendations.

**Query Parameters:**
- `fast_mode` (bool, optional): Use fast mode for quicker processing (default: true)

**Response:**
```json
{
  "message": "Recommendation generation completed",
  "status": "success",
  "fast_mode": true,
  "recommendations_created": 3,
  "timestamp": "2025-08-28T23:32:59.589607",
  "recommendations": [
    {
      "id": 1,
      "symbol": "AAPL",
      "score": 0.85,
      "status": "proposed",
      "created_at": "2025-08-28T23:32:59.589607"
    }
  ]
}
```

#### `GET /v1/recommendations/current`
Get current recommendations.

**Query Parameters:**
- `limit` (int, optional): Number of recommendations to return (default: 10, max: 50)

**Response:**
```json
[
  {
    "id": 1,
    "symbol": "AAPL",
    "strike": 150.0,
    "expiry": "2025-09-19",
    "score": 0.85,
    "rationale": {
      "delta_score": 0.8,
      "iv_score": 0.9,
      "liquidity_score": 0.85
    },
    "status": "proposed",
    "created_at": "2025-08-28T23:32:59.589607"
  }
]
```

#### `GET /v1/recommendations/{recommendation_id}`
Get a specific recommendation by ID.

**Path Parameters:**
- `recommendation_id` (int): Recommendation ID

**Response:**
```json
{
  "id": 1,
  "symbol": "AAPL",
  "strike": 150.0,
  "expiry": "2025-09-19",
  "score": 0.85,
  "rationale": {
    "delta_score": 0.8,
    "iv_score": 0.9,
    "liquidity_score": 0.85
  },
  "status": "proposed",
  "created_at": "2025-08-28T23:32:59.589607"
}
```

#### `PUT /v1/recommendations/{recommendation_id}/status`
Update recommendation status.

**Path Parameters:**
- `recommendation_id` (int): Recommendation ID

**Request Body:**
```json
{
  "status": "approved"
}
```

**Response:**
```json
{
  "message": "Recommendation status updated",
  "recommendation_id": 1,
  "new_status": "approved",
  "timestamp": "2025-08-28T23:32:59.589607"
}
```

### Positions

#### `GET /v1/positions/`
Get all equity positions.

**Response:**
```json
[
  {
    "id": 1,
    "symbol": "AAPL",
    "shares": 100,
    "avg_price": 150.25,
    "current_price": 155.50,
    "market_value": 15550.0,
    "pnl": 525.0,
    "pnl_pct": 3.49,
    "updated_at": "2025-08-28T23:32:59.589607"
  }
]
```

#### `GET /v1/positions/options`
Get all option positions.

**Response:**
```json
[
  {
    "id": 1,
    "symbol": "AAPL",
    "contract_symbol": "AAPL250919P00150000",
    "side": "short",
    "option_type": "put",
    "quantity": 1,
    "strike": 150.0,
    "expiry": "2025-09-19",
    "open_price": 2.50,
    "current_price": 2.25,
    "pnl": 25.0,
    "pnl_pct": 10.0,
    "dte": 22,
    "status": "open",
    "updated_at": "2025-08-28T23:32:59.589607"
  }
]
```

#### `GET /v1/positions/portfolio`
Get portfolio summary.

**Response:**
```json
{
  "cash": 10000.0,
  "equity_value": 15550.0,
  "option_value": 225.0,
  "total_value": 25775.0,
  "total_pnl": 550.0,
  "total_pnl_pct": 2.18,
  "positions": [...],
  "option_positions": [...]
}
```

#### `GET /v1/positions/account`
Get account information.

**Response:**
```json
{
  "account_number": "123456789",
  "total_value": 25775.0,
  "cash": 10000.0,
  "long_stock_value": 15550.0,
  "short_stock_value": 0.0,
  "long_option_value": 0.0,
  "short_option_value": 225.0,
  "buying_power": 15000.0,
  "day_trade_buying_power": 15000.0,
  "equity": 25775.0,
  "last_updated": "2025-08-28T23:32:59.589607"
}
```

#### `POST /v1/positions/sync`
Sync positions from broker.

**Response:**
```json
{
  "message": "Positions synced successfully",
  "equity_positions_synced": 5,
  "option_positions_synced": 3,
  "timestamp": "2025-08-28T23:32:59.589607"
}
```

### Trades

#### `GET /v1/trades/`
Get list of trades with optional filtering.

**Query Parameters:**
- `limit` (int, optional): Number of trades to return (default: 100, max: 1000)
- `offset` (int, optional): Number of trades to skip (default: 0)
- `status` (str, optional): Filter by trade status

**Response:**
```json
[
  {
    "id": 1,
    "symbol": "AAPL",
    "option_symbol": "AAPL250919P00150000",
    "action": "sell",
    "quantity": 1,
    "price": 2.50,
    "status": "executed",
    "created_at": "2025-08-28T23:32:59.589607",
    "executed_at": "2025-08-28T23:32:59.589607",
    "recommendation_id": 1
  }
]
```

#### `GET /v1/trades/{trade_id}`
Get a specific trade by ID.

**Path Parameters:**
- `trade_id` (int): Trade ID

**Response:**
```json
{
  "id": 1,
  "symbol": "AAPL",
  "option_symbol": "AAPL250919P00150000",
  "action": "sell",
  "quantity": 1,
  "price": 2.50,
  "status": "executed",
  "created_at": "2025-08-28T23:32:59.589607",
  "executed_at": "2025-08-28T23:32:59.589607",
  "recommendation_id": 1
}
```

#### `POST /v1/trades/execute/{trade_id}`
Execute a pending trade.

**Path Parameters:**
- `trade_id` (int): Trade ID

**Response:**
```json
{
  "message": "Trade executed successfully",
  "trade_id": 1,
  "result": {
    "order_id": "12345",
    "fill_price": 2.50,
    "fill_time": "2025-08-28T23:32:59.589607"
  }
}
```

### Export

#### `POST /v1/export/transactions.xlsx`
Export all transactions to Excel format.

**Response:** Excel file download

#### `POST /v1/export/recommendations.xlsx`
Export all recommendations to Excel format.

**Response:** Excel file download

#### `POST /v1/export/positions.xlsx`
Export all positions to Excel format.

**Response:** Excel file download

#### `POST /v1/export/portfolio-report.xlsx`
Export comprehensive portfolio report to Excel format.

**Response:** Excel file download

## Error Responses

All endpoints return standard HTTP status codes and error responses in the following format:

```json
{
  "detail": "Error message description"
}
```

Common status codes:
- `200`: Success
- `400`: Bad Request
- `404`: Not Found
- `500`: Internal Server Error

## Rate Limiting

Currently, the API does not implement rate limiting. However, it's recommended to:
- Limit requests to reasonable frequencies
- Use the `fast_mode` parameter for recommendation generation to reduce processing time
- Cache responses when possible

## Data Models

### Recommendation
```json
{
  "id": 1,
  "symbol": "AAPL",
  "strike": 150.0,
  "expiry": "2025-09-19",
  "score": 0.85,
  "rationale": {
    "delta_score": 0.8,
    "iv_score": 0.9,
    "liquidity_score": 0.85
  },
  "status": "proposed",
  "created_at": "2025-08-28T23:32:59.589607"
}
```

### Position
```json
{
  "id": 1,
  "symbol": "AAPL",
  "shares": 100,
  "avg_price": 150.25,
  "current_price": 155.50,
  "market_value": 15550.0,
  "pnl": 525.0,
  "pnl_pct": 3.49,
  "updated_at": "2025-08-28T23:32:59.589607"
}
```

### Option
```json
{
  "symbol": "AAPL",
  "expiry": "2025-09-19",
  "strike": 150.0,
  "option_type": "put",
  "bid": 2.50,
  "ask": 2.55,
  "last": 2.52,
  "delta": -0.45,
  "gamma": 0.02,
  "theta": -0.15,
  "vega": 0.25,
  "implied_volatility": 0.25,
  "open_interest": 1250,
  "volume": 500,
  "dte": 22
}
```

## Development Commands

The project includes a `justfile` with convenient commands:

```bash
# Start the API
just start-api

# View logs
just logs-api

# Test delta parsing
just test-delta-parsing

# Test options fetching
just test-options-fetch

# Generate recommendations (fast mode)
just generate-recommendations-fast

# Generate recommendations (slow mode)
just generate-recommendations-slow
```

## Notes

- All timestamps are in ISO 8601 format (UTC)
- Greeks (delta, gamma, theta, vega) are stored with 2-digit precision
- The API uses Tradier for market data (with fallback to mock data in development)
- Database operations are asynchronous using SQLAlchemy 2.0
- The system implements caching to reduce API calls to external services
