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
  strike?: number
  expiry?: string
  score: number
  rationale: Record<string, any>
  status: string
  created_at: string
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

