'use client'

import { useState, useEffect } from 'react'
import { accountApi, positionsApi, recommendationsApi, tradesApi } from '@/lib/api'
import { AccountBalance, Position, OptionPosition, Recommendation, TradeHistory } from '@/types'
import {
  Box,
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  AppBar,
  Toolbar,
  IconButton,
  Button,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  LinearProgress,
  CircularProgress,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  AccountBalance as AccountBalanceIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material'

export default function Dashboard() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Account data
  const [accountData, setAccountData] = useState<AccountBalance | null>(null)
  
  // Positions data
  const [equityPositions, setEquityPositions] = useState<Position[]>([])
  const [optionPositions, setOptionPositions] = useState<OptionPosition[]>([])
  
  // Recommendations data
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  
  // Trade history data
  const [tradeHistory, setTradeHistory] = useState<TradeHistory[]>([])
  
  // Recommendations refresh state
  const [recommendationsLastUpdated, setRecommendationsLastUpdated] = useState<string | null>(null)
  const [refreshingRecommendations, setRefreshingRecommendations] = useState(false)

  const fetchAllData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Fetch all data in parallel
      const [accountRes, equityRes, optionsRes, recsRes, tradesRes] = await Promise.allSettled([
        accountApi.getAccountInfo(),
        positionsApi.getAll(),
        positionsApi.getOptions(),
        recommendationsApi.getCurrent(),
        tradesApi.getHistory(),
      ])
      
      // Handle account data
      if (accountRes.status === 'fulfilled') {
        setAccountData(accountRes.value.data)
      }
      
      // Handle equity positions
      if (equityRes.status === 'fulfilled') {
        setEquityPositions(equityRes.value.data)
      }
      
      // Handle option positions
      if (optionsRes.status === 'fulfilled') {
        setOptionPositions(optionsRes.value.data)
      }
      
      // Handle recommendations
      if (recsRes.status === 'fulfilled') {
        setRecommendations(recsRes.value.data)
        setRecommendationsLastUpdated(new Date().toISOString())
      }
      
      // Handle trade history
      if (tradesRes.status === 'fulfilled') {
        setTradeHistory(tradesRes.value.data)
      }
      
    } catch (err) {
      console.error('Error fetching data:', err)
      setError('Failed to fetch data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAllData()
  }, [])

  const handleRefresh = () => {
    fetchAllData()
  }

  const handleRefreshRecommendations = async () => {
    try {
      setRefreshingRecommendations(true)
      setError(null)
      
      // Call the refresh endpoint
      await recommendationsApi.refresh()
      
      // Fetch updated recommendations
      const recsRes = await recommendationsApi.getCurrent()
      setRecommendations(recsRes.data)
      setRecommendationsLastUpdated(new Date().toISOString())
      
    } catch (err) {
      console.error('Error refreshing recommendations:', err)
      setError('Failed to refresh recommendations')
    } finally {
      setRefreshingRecommendations(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Header */}
      <AppBar position="static">
        <Toolbar>
          <AccountBalanceIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Wheel Strategy Dashboard
          </Typography>
          <IconButton color="inherit" onClick={handleRefresh} disabled={loading}>
            {loading ? <CircularProgress size={24} color="inherit" /> : <RefreshIcon />}
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Container maxWidth="xl" sx={{ flexGrow: 1, py: 3 }}>
        {loading && <LinearProgress sx={{ mb: 2 }} />}
        
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Account Summary Cards */}
        {accountData && (
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Account Number
                  </Typography>
                  <Typography variant="h6" component="div">
                    {accountData.account_number}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Tradier Account
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Total Value
                  </Typography>
                  <Typography variant="h4" component="div">
                    {formatCurrency(accountData.total_value)}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Portfolio Value
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Available Cash
                  </Typography>
                  <Typography variant="h4" component="div">
                    {formatCurrency(accountData.cash)}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Ready to deploy
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Buying Power
                  </Typography>
                  <Typography variant="h4" component="div">
                    {formatCurrency(accountData.buying_power)}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Day Trade: {formatCurrency(accountData.day_trade_buying_power)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Main Content - Vertical Layout */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* Recommendations */}
          <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <TrendingUpIcon sx={{ mr: 1 }} />
                    <Typography variant="h6" component="div">
                      Current Recommendations
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {recommendationsLastUpdated && (
                      <Typography variant="caption" color="textSecondary">
                        Updated: {formatDate(recommendationsLastUpdated)}
                      </Typography>
                    )}
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<RefreshIcon />}
                      onClick={handleRefreshRecommendations}
                      disabled={refreshingRecommendations}
                    >
                      {refreshingRecommendations ? 'Refreshing...' : 'Refresh'}
                    </Button>
                  </Box>
                </Box>
                
                {recommendations.length === 0 ? (
                  <Typography color="textSecondary" align="center" sx={{ py: 4 }}>
                    No current recommendations
                  </Typography>
                ) : (
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Symbol</TableCell>
                          <TableCell>Score</TableCell>
                          <TableCell>Status</TableCell>
                          <TableCell>Created</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                                                 {recommendations.map((rec: Recommendation) => (
                          <TableRow key={rec.id}>
                            <TableCell>
                              <Typography variant="body2" fontWeight="bold">
                                {rec.symbol}
                              </Typography>
                              {rec.strike && (
                                <Typography variant="caption" color="textSecondary">
                                  Strike: {rec.strike}
                                </Typography>
                              )}
                            </TableCell>
                            <TableCell>
                              <Chip 
                                label={`${rec.score.toFixed(1)}`}
                                size="small"
                                color={rec.score >= 7 ? 'success' : rec.score >= 5 ? 'warning' : 'error'}
                              />
                            </TableCell>
                            <TableCell>
                              <Chip 
                                label={rec.status}
                                size="small"
                                variant="outlined"
                              />
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2">
                                {formatDate(rec.created_at)}
                              </Typography>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </CardContent>
            </Card>

          {/* Current Positions */}
          <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <AccountBalanceIcon sx={{ mr: 1 }} />
                  <Typography variant="h6" component="div">
                    Current Positions
                  </Typography>
                </Box>
                
                {equityPositions.length === 0 && optionPositions.length === 0 ? (
                  <Typography color="textSecondary" align="center" sx={{ py: 4 }}>
                    No current positions
                  </Typography>
                ) : (
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Symbol</TableCell>
                          <TableCell>Type</TableCell>
                          <TableCell>Quantity</TableCell>
                          <TableCell>Avg Price</TableCell>
                          <TableCell>P&L</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {/* Equity Positions */}
                                                 {equityPositions.map((pos: Position) => (
                          <TableRow key={`equity-${pos.id}`}>
                            <TableCell>
                              <Typography variant="body2" fontWeight="bold">
                                {pos.symbol}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Chip label="Stock" size="small" color="primary" />
                            </TableCell>
                            <TableCell>{pos.shares}</TableCell>
                            <TableCell>{formatCurrency(pos.avg_price)}</TableCell>
                            <TableCell>
                              {pos.pnl !== undefined && (
                                <Typography
                                  variant="body2"
                                  color={pos.pnl >= 0 ? 'success.main' : 'error.main'}
                                  fontWeight="bold"
                                >
                                  {formatCurrency(pos.pnl)}
                                </Typography>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                        
                        {/* Option Positions */}
                                                 {optionPositions.map((pos: OptionPosition) => (
                          <TableRow key={`option-${pos.id}`}>
                            <TableCell>
                              <Typography variant="body2" fontWeight="bold">
                                {pos.symbol}
                              </Typography>
                              <Typography variant="caption" color="textSecondary">
                                {pos.contract_symbol}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Chip 
                                label={`${pos.option_type} ${pos.side}`}
                                size="small"
                                color="secondary"
                              />
                            </TableCell>
                            <TableCell>{pos.quantity}</TableCell>
                            <TableCell>{formatCurrency(pos.open_price)}</TableCell>
                            <TableCell>
                              {pos.pnl !== undefined && (
                                <Typography
                                  variant="body2"
                                  color={pos.pnl >= 0 ? 'success.main' : 'error.main'}
                                  fontWeight="bold"
                                >
                                  {formatCurrency(pos.pnl)}
                                </Typography>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </CardContent>
            </Card>

          {/* Orders History */}
          <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <TimelineIcon sx={{ mr: 1 }} />
                  <Typography variant="h6" component="div">
                    Orders History
                  </Typography>
                </Box>
                
                {tradeHistory.length === 0 ? (
                  <Typography color="textSecondary" align="center" sx={{ py: 4 }}>
                    No trade history available
                  </Typography>
                ) : (
                  <TableContainer component={Paper} variant="outlined">
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Symbol</TableCell>
                          <TableCell>Action</TableCell>
                          <TableCell>Quantity</TableCell>
                          <TableCell>Price</TableCell>
                          <TableCell>Status</TableCell>
                          <TableCell>Created</TableCell>
                          <TableCell>Executed</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                                                 {tradeHistory.map((trade: TradeHistory) => (
                          <TableRow key={trade.id}>
                            <TableCell>
                              <Typography variant="body2" fontWeight="bold">
                                {trade.symbol}
                              </Typography>
                              {trade.option_symbol && (
                                <Typography variant="caption" color="textSecondary">
                                  {trade.option_symbol}
                                </Typography>
                              )}
                            </TableCell>
                            <TableCell>
                              <Chip 
                                label={trade.action}
                                size="small"
                                color={trade.action.includes('buy') ? 'success' : 'error'}
                              />
                            </TableCell>
                            <TableCell>{trade.quantity}</TableCell>
                            <TableCell>{formatCurrency(trade.price)}</TableCell>
                            <TableCell>
                              <Chip 
                                label={trade.status}
                                size="small"
                                variant="outlined"
                                color={
                                  trade.status === 'filled' ? 'success' :
                                  trade.status === 'pending' ? 'warning' :
                                  trade.status === 'cancelled' ? 'error' : 'default'
                                }
                              />
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2">
                                {formatDate(trade.created_at)}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              {trade.executed_at ? (
                                <Typography variant="body2">
                                  {formatDate(trade.executed_at)}
                                </Typography>
                              ) : (
                                <Typography variant="body2" color="textSecondary">
                                  -
                                </Typography>
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </CardContent>
            </Card>
        </Box>
      </Container>
    </Box>
  )
}
