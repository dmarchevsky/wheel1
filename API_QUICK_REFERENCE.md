# Wheel Strategy API - Quick Reference

## Most Common Endpoints

### Health Check
```bash
# Basic health check
curl -X GET "http://localhost:8000/health/"

# Detailed health with database status
curl -X GET "http://localhost:8000/health/ready"
```

### Market Data
```bash
# Get interesting tickers
curl -X GET "http://localhost:8000/v1/market-data/interesting-tickers" | jq '.tickers | length'

# Fetch options for a specific ticker
curl -X POST "http://localhost:8000/v1/market-data/tickers/AAPL/options" | jq .

# Test delta parsing (debugging)
curl -X GET "http://localhost:8000/v1/market-data/test-delta-parsing" | jq .
```

### Recommendations
```bash
# Generate recommendations (fast mode)
curl -X POST "http://localhost:8000/v1/recommendations/generate?fast_mode=true" | jq .

# Generate recommendations (slow mode)
curl -X POST "http://localhost:8000/v1/recommendations/generate?fast_mode=false" | jq .

# Get current recommendations
curl -X GET "http://localhost:8000/v1/recommendations/current" | jq .
```

### Positions
```bash
# Get all positions
curl -X GET "http://localhost:8000/v1/positions/" | jq '.positions | length'

# Get portfolio summary
curl -X GET "http://localhost:8000/v1/positions/portfolio" | jq .

# Get account info
curl -X GET "http://localhost:8000/v1/positions/account" | jq .
```

### Trades
```bash
# Get recent trades
curl -X GET "http://localhost:8000/v1/trades/" | jq .
```

## Using justfile Commands

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

## Common Response Patterns

### Success Response
```json
{
  "message": "Operation completed",
  "status": "success",
  "timestamp": "2025-08-28T23:32:59.589607",
  "data": {...}
}
```

### Error Response
```json
{
  "detail": "Error message description"
}
```

## Key Data Fields

### Options Greeks (2-digit precision)
- `delta`: -1.0 to 1.0 (negative for puts, positive for calls)
- `gamma`: 0.0 to 1.0 (rate of change of delta)
- `theta`: Usually negative (time decay)
- `vega`: Usually positive (volatility sensitivity)
- `implied_volatility`: 0.0 to 1.0 (as decimal)

### Recommendation Status
- `proposed`: New recommendation
- `approved`: Approved for execution
- `rejected`: Rejected
- `executed`: Trade executed
- `expired`: Recommendation expired

### Trade Status
- `pending`: Trade created but not executed
- `executed`: Trade successfully executed
- `cancelled`: Trade cancelled
- `failed`: Trade failed to execute

## Troubleshooting

### Check if API is running
```bash
curl -X GET "http://localhost:8000/health/"
```

### Check database connectivity
```bash
curl -X GET "http://localhost:8000/health/ready"
```

### View API logs
```bash
just logs-api
```

### Test specific functionality
```bash
# Test options data fetching
just test-options-fetch

# Test delta parsing
just test-delta-parsing
```
