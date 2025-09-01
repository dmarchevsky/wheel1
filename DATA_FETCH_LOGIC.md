# Data Fetch Logic Implementation

This document describes the updated data fetch logic for the Wheel Strategy application, organized into three main components with specific scheduling requirements.

## Overview

The new data fetch logic is designed to efficiently manage market data updates with proper separation of concerns and optimal scheduling:

1. **Market Population** (Monthly or by demand)
2. **Universe Scoring** (Daily)
3. **Recommendations** (Daily)

## 1. Market Population

### Purpose
Populate and maintain the complete universe of interesting tickers with fundamental data.

### Components

#### 1a. SP500 Universe Update
- **Frequency**: Monthly or by demand
- **Function**: `update_sp500_universe()`
- **Actions**:
  - Fetch current S&P 500 constituents from API Ninjas
  - Add new companies to `interesting_tickers`
  - Remove/deactivate companies no longer in S&P 500
  - Set source as "sp500" for tracking

#### 1b. Fundamentals Update
- **Frequency**: Monthly or by demand
- **Function**: `update_all_fundamentals()`
- **Data Sources**:
  - **Financial Modeling Prep (FMP) API**: Company name, sector, industry, market cap, beta, P/E ratio, dividend yield, volume
  - **API Ninjas**: Earnings dates (fallback for market cap)
  - **Tradier API**: Additional fundamentals (fallback)

### API Endpoints
- `POST /v1/market-data/market-population` - Complete market population
- `POST /v1/market-data/update-all-fundamentals` - Fundamentals only

### CLI Commands
```bash
just market-population    # Complete market population
just update-fundamentals  # Fundamentals only
```

## 2. Universe Scoring (Wheel Strategy Optimized)

### Purpose
Calculate universe scores specifically optimized for the Wheel Strategy, prioritizing stocks suitable for selling cash-secured puts and covered calls.

### Frequency
Daily

### Function
`calculate_universe_scores()`

### Scoring Components (Weighted)

#### 1. **Options Suitability** (40% of total score)
- **Open Interest**: High liquidity for options trading
  - > 10,000: +0.4 points (High liquidity)
  - > 5,000: +0.3 points (Good liquidity)
  - > 2,000: +0.2 points (Moderate liquidity)
  - > 500: +0.1 points (Minimum liquidity)

- **Volume Activity**: Active options trading
  - > 5,000: +0.3 points
  - > 2,000: +0.2 points
  - > 500: +0.1 points

- **Implied Volatility**: Sweet spot for premium selling
  - 20-60%: +0.3 points (Optimal range)
  - 10-80%: +0.2 points (Acceptable range)
  - > 80%: +0.1 points (High premium, higher risk)

#### 2. **Technical Setup** (25% of total score)
- **Volatility Sweet Spot**: 15-35% (optimal for wheel strategy)
  - 15-35%: +0.3 points (Sweet spot)
  - 10-50%: +0.2 points (Acceptable)
  - < 10%: +0.1 points (Too stable, low premiums)
  - > 50%: +0.1 points (Too volatile, high risk)

- **Support Level Proximity**: Prefer stocks near support for put selling
  - Large caps (>$50B): 12% below current price
  - Mid caps ($10-50B): 18% below current price
  - Small caps (<$10B): 25% below current price

- **Volume Strength**: Healthy trading activity
  - > 1M avg volume: +0.3 points

#### 3. **Fundamental Quality** (20% of total score)
- **Company Size & Stability**:
  - > $100B: +0.4 points (Very stable)
  - > $50B: +0.35 points (Stable)
  - > $20B: +0.3 points (Good)
  - > $10B: +0.25 points (Acceptable)
  - > $5B: +0.2 points (Minimum for wheel)

- **Valuation Quality**:
  - P/E 8-30: +0.3 points (Reasonable)
  - P/E 5-40: +0.2 points (Acceptable)
  - P/E < 5: +0.1 points (Potential value trap)
  - P/E > 40: +0.1 points (Expensive, higher risk)

- **Financial Health**:
  - Beta 0.6-1.4: +0.3 points (Moderate volatility)
  - Beta 0.4-1.6: +0.2 points (Acceptable range)
  - Beta < 0.4: +0.1 points (Too stable, low premiums)
  - Beta > 1.6: +0.1 points (Too volatile, high risk)

- **Dividend Stability**: +0.1 points for dividend-paying stocks

#### 4. **Risk Assessment** (15% of total score)
- **Earnings Blackout Risk**:
  - > 30 days: +0.4 points (Low risk)
  - > 14 days: +0.3 points (Medium risk)
  - > 7 days: +0.2 points (Higher risk)
  - > 0 days: +0.1 points (High risk)

- **Sector Risk Assessment**:
  - Low risk: Consumer Staples, Utilities, Healthcare, Real Estate (+0.3)
  - Medium risk: Consumer Discretionary, Industrials, Materials, Communication Services (+0.2)
  - High risk: Technology, Energy, Financial Services (+0.1)

- **Market Cap Stability**: Higher scores for larger, more stable companies

### API Endpoints
- `POST /v1/market-data/calculate-universe-scores`

### CLI Commands
```bash
just calculate-universe-scores
```

## 3. Recommendations

### Purpose
Update ticker quotes and option chains for analysis and recommendation generation.

### Frequency
Daily

### Components

#### 3a. Recommendation Ticker Updates
- **Function**: `update_recommendation_tickers()`
- **Scope**:
  - Top 20 S&P 500 tickers by universe score
  - All manually added tickers (source = "manual")
- **Actions**:
  - Update ticker quotes with fresh market data
  - Update option chains for analysis

### API Endpoints
- `POST /v1/market-data/update-recommendation-tickers`

### CLI Commands
```bash
just update-recommendation-tickers
```

## Scheduled Jobs

The worker automatically runs these jobs on the following schedule:

### Monthly Jobs
- **Market Population**: First day of each month at 6:00 AM PST
  - Updates SP500 universe
  - Updates all fundamentals

### Daily Jobs
- **Universe Scoring**: Every day at 7:00 AM PST
  - Calculates scores for all active tickers

- **Recommendation Updates**: Every day at 8:00 AM PST (market open)
  - Updates quotes and options for top 20 SP500 + manual tickers

- **Market Data Refresh**: Every hour during market hours
  - Refreshes quotes for tickers needing updates

## Data Sources

### Financial Modeling Prep (FMP) API
- **Endpoint**: https://financialmodelingprep.com/api/v3/profile/{symbol}
- **Purpose**: Company name, sector, industry, market cap, beta, volume, P/E ratio, dividend yield
- **Configuration**: `FMP_API_KEY` environment variable
- **Documentation**: [FMP API Documentation](https://site.financialmodelingprep.com/developer/docs#profile-symbol)

### API Ninjas
- **Purpose**: S&P 500 constituents, earnings dates, market cap
- **Configuration**: `API_NINJAS_API_KEY` environment variable

### Tradier API
- **Purpose**: Real-time quotes, fundamentals (P/E, beta, dividend yield), options
- **Configuration**: `TRADIER_ACCESS_TOKEN` environment variable

## Error Handling

- **Rate Limiting**: Built-in delays between API calls
- **Retry Logic**: Failed updates are logged but don't stop the process
- **Partial Success**: Jobs continue even if some tickers fail
- **Notifications**: Telegram notifications for job completion status

## Monitoring

### Logs
All operations are logged with appropriate levels:
- `INFO`: Job start/completion, successful updates
- `WARNING`: Missing data, API failures
- `ERROR`: Critical failures, exceptions

### Metrics
Each job returns detailed metrics:
- Success/failure counts
- Processing times
- Affected ticker counts

### Notifications
Telegram notifications are sent for:
- Job completion status
- Success rates
- Error summaries

## Testing

Run the test script to verify functionality:
```bash
python test_new_data_fetch.py
```

## Configuration

### Environment Variables
```bash
# Required for Financial Modeling Prep API
FMP_API_KEY=your_fmp_api_key

# Required for API Ninjas
API_NINJAS_API_KEY=your_api_ninjas_key

# Required for Tradier
TRADIER_ACCESS_TOKEN=your_tradier_token
```

### Database Schema
The system uses the existing `interesting_tickers` table with additional fields:
- `universe_score`: Calculated daily score (0.0-1.0)
- `last_analysis_date`: Timestamp of last scoring
- `source`: "sp500" or "manual" for tracking

## Migration Notes

- Legacy methods are preserved for backward compatibility
- New endpoints are additive and don't break existing functionality
- The system gracefully handles missing API keys
- Rate limiting prevents API quota exhaustion
- **FMP API Integration**: Replaces SEC API with more comprehensive data from Financial Modeling Prep
- **Enhanced Data Quality**: FMP provides more reliable and comprehensive company profiles
- **Fallback Strategy**: Maintains API Ninjas and Tradier as fallbacks for data completeness

## Wheel Strategy Optimization

The universe scoring system has been completely redesigned to optimize for the Wheel Strategy:

### **Key Improvements**

1. **Options-First Approach**: 40% of scoring focuses on options suitability (liquidity, volume, IV)
2. **Technical Setup**: 25% considers volatility sweet spots and support levels for put selling
3. **Fundamental Quality**: 20% ensures company stability and reasonable valuations
4. **Risk Management**: 15% assesses earnings blackouts and sector-specific risks

### **Wheel Strategy Benefits**

- **Better Put Opportunities**: Prioritizes stocks with optimal volatility and support levels
- **Covered Call Readiness**: Focuses on stable, dividend-paying companies
- **Risk Reduction**: Avoids earnings blackouts and overly volatile stocks
- **Premium Optimization**: Targets stocks in the volatility sweet spot (15-35%)
- **Liquidity Focus**: Ensures sufficient options volume and open interest

### **Scoring Philosophy**

The new system moves away from generic "buy-and-hold" scoring to **options trading optimization**:
- **Before**: Favored large-cap, low-beta stocks (good for long-term holding)
- **After**: Prioritizes stocks optimal for selling puts and calls (wheel strategy focus)

This ensures the universe selection directly supports the wheel strategy's goal of generating consistent premium income through options trading.
