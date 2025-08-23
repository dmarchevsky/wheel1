'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { TrendingUp, TrendingDown, DollarSign, Calendar, Target } from 'lucide-react'

interface Recommendation {
  id: number
  symbol: string
  strike: number | null
  expiry: string | null
  score: number
  rationale: {
    annualized_yield: number
    proximity_score: number
    liquidity_score: number
    risk_adjustment: number
    qualitative_score: number
    dte: number
    spread_pct: number
    mid_price: number
  }
  status: string
  created_at: string
}

interface Portfolio {
  cash: number
  equity_value: number
  option_value: number
  total_value: number
  total_pnl: number
  total_pnl_pct: number
  positions: any[]
  option_positions: any[]
}

export default function Dashboard() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [recsRes, portfolioRes] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/recommendations/current`),
        fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/v1/positions/portfolio`)
      ])

      if (recsRes.ok) {
        const recs = await recsRes.json()
        setRecommendations(recs)
      }

      if (portfolioRes.ok) {
        const port = await portfolioRes.json()
        setPortfolio(port)
      }
    } catch (error) {
      console.error('Error fetching data:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount)
  }

  const formatPercentage = (value: number) => {
    return `${value.toFixed(2)}%`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary mx-auto"></div>
          <p className="mt-4 text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Wheel Strategy Dashboard</h1>
          <p className="text-muted-foreground">AI-powered options trading recommendations</p>
        </div>
        <Button onClick={fetchData} variant="outline">
          Refresh
        </Button>
      </div>

      {/* Portfolio Summary */}
      {portfolio && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Value</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(portfolio.total_value)}</div>
              <p className="text-xs text-muted-foreground">
                {portfolio.total_pnl >= 0 ? '+' : ''}{formatCurrency(portfolio.total_pnl)} ({formatPercentage(portfolio.total_pnl_pct)})
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Cash</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(portfolio.cash)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Equity Value</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(portfolio.equity_value)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Options Value</CardTitle>
              <Target className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(portfolio.option_value)}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Content */}
      <Tabs defaultValue="recommendations" className="space-y-4">
        <TabsList>
          <TabsTrigger value="recommendations">Current Recommendations</TabsTrigger>
          <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="recommendations" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recommendations.map((rec) => (
              <Card key={rec.id} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-xl">{rec.symbol}</CardTitle>
                      <CardDescription>
                        {rec.strike && `Strike: $${rec.strike}`}
                        {rec.expiry && ` • Expires: ${new Date(rec.expiry).toLocaleDateString()}`}
                      </CardDescription>
                    </div>
                    <Badge variant={rec.status === 'proposed' ? 'default' : 'secondary'}>
                      {rec.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium">Score</span>
                      <span className="text-sm text-muted-foreground">{formatPercentage(rec.score * 100)}</span>
                    </div>
                    <Progress value={rec.score * 100} className="h-2" />
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">Annualized Yield:</span>
                      <div className="font-medium">{formatPercentage(rec.rationale.annualized_yield)}</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">DTE:</span>
                      <div className="font-medium">{rec.rationale.dte}</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Spread:</span>
                      <div className="font-medium">{formatPercentage(rec.rationale.spread_pct)}</div>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Mid Price:</span>
                      <div className="font-medium">${rec.rationale.mid_price?.toFixed(2)}</div>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button size="sm" className="flex-1">
                      Execute
                    </Button>
                    <Button size="sm" variant="outline">
                      Details
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {recommendations.length === 0 && (
            <Card>
              <CardContent className="flex items-center justify-center h-32">
                <p className="text-muted-foreground">No current recommendations</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="portfolio" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Equity Positions */}
            <Card>
              <CardHeader>
                <CardTitle>Equity Positions</CardTitle>
              </CardHeader>
              <CardContent>
                {portfolio?.positions && portfolio.positions.length > 0 ? (
                  <div className="space-y-3">
                    {portfolio.positions.map((position, index) => (
                      <div key={index} className="flex justify-between items-center p-3 border rounded-lg">
                        <div>
                          <div className="font-medium">{position.symbol}</div>
                          <div className="text-sm text-muted-foreground">
                            {position.shares} shares @ {formatCurrency(position.avg_price)}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-medium">{formatCurrency(position.market_value || 0)}</div>
                          <div className={`text-sm ${position.pnl && position.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {position.pnl ? `${position.pnl >= 0 ? '+' : ''}${formatCurrency(position.pnl)}` : 'N/A'}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground text-center py-8">No equity positions</p>
                )}
              </CardContent>
            </Card>

            {/* Option Positions */}
            <Card>
              <CardHeader>
                <CardTitle>Option Positions</CardTitle>
              </CardHeader>
              <CardContent>
                {portfolio?.option_positions && portfolio.option_positions.length > 0 ? (
                  <div className="space-y-3">
                    {portfolio.option_positions.map((position, index) => (
                      <div key={index} className="flex justify-between items-center p-3 border rounded-lg">
                        <div>
                          <div className="font-medium">{position.symbol}</div>
                          <div className="text-sm text-muted-foreground">
                            {position.option_type.toUpperCase()} {position.strike} • {position.dte} DTE
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-medium">{formatCurrency(position.open_price)}</div>
                          <div className={`text-sm ${position.pnl && position.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {position.pnl ? `${position.pnl >= 0 ? '+' : ''}${formatCurrency(position.pnl)}` : 'N/A'}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground text-center py-8">No option positions</p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardContent className="flex items-center justify-center h-32">
              <p className="text-muted-foreground">Trade history coming soon...</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
