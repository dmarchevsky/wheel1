export interface Position {
  id: number
  symbol: string
  shares: number
  avg_price: number
  current_price?: number
  market_value?: number
  pnl?: number
  pnl_pct?: number
  updated_at: string
}

export interface OptionPosition {
  id: number
  symbol: string
  contract_symbol: string
  side: string
  option_type: string
  quantity: number
  strike: number
  expiry: string
  open_price: number
  current_price?: number
  pnl?: number
  pnl_pct?: number
  dte?: number
  status: string
  updated_at: string
}

export interface Recommendation {
  id: number
  symbol: string
  name?: string  // Company name
  option_symbol?: string
  option_type: string  // Side put or call
  underlying_ticker: string  // Underlying ticker
  current_price?: number
  strike?: number
  expiry?: string
  dte?: number
  contract_price?: number  // Calculated contract price
  total_credit?: number
  collateral?: number
  industry?: string
  sector?: string
  next_earnings_date?: string
  annualized_roi?: number  // Annualized ROI
  pe_ratio?: number
  put_call_ratio?: number
  volume?: number
  score: number
  score_breakdown?: Record<string, string>  // Score components in human readable format
  rationale: Record<string, any>
  status: string
  created_at: string
  
  // Expanded rationale fields (keeping for backward compatibility)
  annualized_yield?: number
  proximity_score?: number
  liquidity_score?: number
  risk_adjustment?: number
  qualitative_score?: number
  spread_pct?: number
  mid_price?: number
  delta?: number
  iv_rank?: number
  open_interest?: number
  probability_of_profit_black_scholes?: number
  probability_of_profit_monte_carlo?: number
  option_side?: string  // 'put' or 'call'
}

export interface AccountBalance {
  account_number: string
  total_value: number
  cash: number
  long_stock_value: number
  short_stock_value: number
  long_option_value: number
  short_option_value: number
  buying_power: number
  day_trade_buying_power: number
  equity: number
  last_updated: string
}

export interface Portfolio {
  positions: Position[]
  totalPnl: number
  totalPnlPercent: number
  totalValue: number
  availableCash: number
}

export interface TradeHistory {
  id: number
  symbol: string
  option_symbol?: string
  action: string
  quantity: number
  price: number
  status: string
  created_at: string
  executed_at?: string
  recommendation_id?: number
}

export interface ActivityEvent {
  date: string
  type: string
  symbol?: string
  description: string
  quantity?: number
  price?: number
  amount: number
  balance?: number
}

export interface ApiResponse<T> {
  data: T
  message?: string
  error?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  limit: number
  totalPages: number
}

