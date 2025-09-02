# Portfolio Section Implementation

## Overview
The Portfolio section has been implemented to fetch and display real stock and options positions from the Tradier API. This provides users with live, accurate data from their actual trading account.

## Features

### Real Data Integration
- **Stock Positions**: Fetches equity positions directly from Tradier API with current market prices
- **Options Positions**: Displays option contracts with real-time pricing
- **Account Balances**: Shows actual cash balance and total account value
- **Live P&L Calculations**: Computes profit/loss using current market prices vs. cost basis

### User Interface
- **Portfolio Summary**: Overview cards showing total value, cash, stock value, and options value
- **Stock Positions Table**: Detailed table with symbol, shares, avg price, current price, market value, and P&L
- **Options Positions Table**: Comprehensive options display with contract details, side, quantity, and P&L
- **Real-time Updates**: Refresh buttons to fetch latest data from Tradier
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Implementation Details

### Backend (`/app/backend/routers/positions.py`)
- Enhanced `/v1/positions/portfolio` endpoint to fetch real data from Tradier API
- Uses `TradierClient.get_account_positions()` to retrieve current positions
- Fetches real-time quotes for each position using `get_quote()` method
- Calculates live P&L using current market prices vs. cost basis
- Handles both equity and option positions separately
- Includes error handling with fallback to prevent API failures

### Frontend Components
- **Portfolio Component** (`/app/frontend/src/components/Portfolio.tsx`):
  - Fetches data from `/v1/positions/portfolio` endpoint
  - Displays portfolio summary with key metrics
  - Renders separate tables for stocks and options
  - Includes expand/collapse functionality
  - Shows P&L with color coding (green for gains, red for losses)

- **Portfolio Page** (`/app/frontend/src/app/portfolio/page.tsx`):
  - Dedicated page for portfolio view
  - Accessible via `/portfolio` route

- **Navigation Update** (`/app/frontend/src/components/SideMenu.tsx`):
  - Added Portfolio menu item with AccountBalance icon

## API Endpoints

### GET `/v1/positions/portfolio`
Returns comprehensive portfolio data with real positions from Tradier API.

**Response Structure:**
```json
{
  "cash": 5000.00,
  "equity_value": 25000.00,
  "option_value": 2500.00,
  "total_value": 32500.00,
  "total_pnl": 1250.00,
  "total_pnl_pct": 4.00,
  "positions": [
    {
      "id": 0,
      "symbol": "AAPL",
      "shares": 100,
      "avg_price": 150.00,
      "current_price": 155.00,
      "market_value": 15500.00,
      "pnl": 500.00,
      "pnl_pct": 3.33,
      "updated_at": "2024-01-01T12:00:00"
    }
  ],
  "option_positions": [
    {
      "id": 0,
      "symbol": "AAPL",
      "contract_symbol": "AAPL240119C00150000",
      "side": "long",
      "option_type": "call",
      "quantity": 1,
      "strike": 150.00,
      "expiry": "2024-01-19",
      "open_price": 5.00,
      "current_price": 7.50,
      "pnl": 250.00,
      "pnl_pct": 50.00,
      "dte": 15,
      "status": "open",
      "updated_at": "2024-01-01T12:00:00"
    }
  ]
}
```

## Data Sources

### Real Tradier API Data
- **Positions**: Retrieved from `GET /accounts/{account_id}/positions`
- **Quotes**: Current prices from `GET /markets/quotes`
- **Account Balances**: From `GET /accounts/{account_id}/balances`

### Data Warning Notice
The interface clearly indicates when real Tradier API data is being used:
> "⚠️ Using real Tradier API data - Positions and prices are live from your trading account"

## Error Handling
- Graceful degradation if Tradier API is unavailable
- Clear error messages with retry functionality
- Fallback to empty portfolio data with user notification
- Loading states during API calls

## Security Considerations
- Tradier API credentials are securely stored in environment variables
- All API calls use authenticated requests with Bearer tokens
- Account ID validation ensures only authorized account access

## Usage
1. Navigate to the Portfolio section from the side menu
2. View real-time portfolio summary with total value and P&L
3. Expand/collapse stock and options tables as needed
4. Use refresh buttons to update data from Tradier
5. Monitor P&L with color-coded indicators

## Future Enhancements
- Option Greeks display (delta, gamma, theta, vega)
- Advanced filtering and sorting options
- Export functionality for positions data
- Historical P&L charts
- Position alerts and notifications
