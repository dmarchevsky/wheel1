export interface Position {
  id: number
  symbol: string
  type: 'PUT' | 'CALL'
  strike: number
  expiry: string
  quantity: number
  avgPrice: number
  currentPrice: number
  pnl: number
  pnlPercent: number
  delta?: number
  gamma?: number
  theta?: number
  vega?: number
  iv?: number
}

export interface Recommendation {
  id: number
  symbol: string
  strategy: string
  confidence: number
  expectedReturn: number
  risk: 'Low' | 'Medium' | 'High'
  description?: string
  entryPrice?: number
  targetPrice?: number
  stopLoss?: number
}

export interface AccountBalance {
  cash: number
  buyingPower: number
  dayTradeBuyingPower: number
  equity: number
  marketValue: number
  totalValue: number
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
  type: 'BUY' | 'SELL'
  quantity: number
  price: number
  timestamp: string
  pnl?: number
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

