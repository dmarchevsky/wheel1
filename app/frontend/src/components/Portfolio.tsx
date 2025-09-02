'use client'

import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardHeader,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Alert,
  CircularProgress,
  IconButton,
  Collapse,
  Grid,
  useTheme,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Refresh as RefreshIcon,
  TrendingUp,
  TrendingDown,
  AccountBalance,
} from '@mui/icons-material'
import { accountApi } from '@/lib/api'
import { Position, OptionPosition } from '@/types'

interface PortfolioData {
  cash: number
  equity_value: number
  option_value: number
  total_value: number
  total_pnl: number
  total_pnl_pct: number
  positions: Position[]
  option_positions: OptionPosition[]
}

export default function Portfolio() {
  const theme = useTheme()
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stockExpanded, setStockExpanded] = useState(true)
  const [optionsExpanded, setOptionsExpanded] = useState(true)

  const fetchPortfolio = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await accountApi.getPortfolio()
      setPortfolio(response.data)
    } catch (err: any) {
      console.error('Error fetching portfolio:', err)
      setError(err.response?.data?.detail || 'Failed to fetch portfolio data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPortfolio()
  }, [])

  const formatCurrency = (value: number | undefined | null) => {
    if (value === undefined || value === null) return '$0.00'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value)
  }

  const formatPercent = (value: number | undefined | null) => {
    if (value === undefined || value === null) return '0.00%'
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  const getPnLColor = (value: number | undefined | null) => {
    if (value === undefined || value === null || value === 0) return theme.palette.text.secondary
    return value > 0 ? theme.palette.success.main : theme.palette.error.main
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Alert severity="error" action={
        <IconButton onClick={fetchPortfolio} color="inherit" size="small">
          <RefreshIcon />
        </IconButton>
      }>
        {error}
      </Alert>
    )
  }

  if (!portfolio) {
    return (
      <Alert severity="warning">
        No portfolio data available. Please check your Tradier API configuration.
      </Alert>
    )
  }

  return (
    <Box>
      {/* Portfolio Summary */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={1}>
                <AccountBalance sx={{ mr: 1, color: theme.palette.primary.main }} />
                <Typography variant="h6">Total Value</Typography>
              </Box>
              <Typography variant="h4" fontWeight="bold">
                {formatCurrency(portfolio.total_value)}
              </Typography>
              <Typography 
                variant="body2" 
                color={getPnLColor(portfolio.total_pnl)}
                sx={{ display: 'flex', alignItems: 'center', mt: 1 }}
              >
                {portfolio.total_pnl >= 0 ? <TrendingUp fontSize="small" /> : <TrendingDown fontSize="small" />}
                {formatCurrency(portfolio.total_pnl)} ({formatPercent(portfolio.total_pnl_pct)})
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" mb={1}>Cash</Typography>
              <Typography variant="h4" fontWeight="bold" color={theme.palette.success.main}>
                {formatCurrency(portfolio.cash)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" mb={1}>Stock Value</Typography>
              <Typography variant="h4" fontWeight="bold">
                {formatCurrency(portfolio.equity_value)}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {portfolio.positions.length} positions
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" mb={1}>Options Value</Typography>
              <Typography variant="h4" fontWeight="bold">
                {formatCurrency(portfolio.option_value)}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {portfolio.option_positions.length} contracts
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Stock Positions Table */}
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title={`Stock Positions (${portfolio.positions.length})`}
          action={
            <Box>
              <IconButton onClick={fetchPortfolio} size="small">
                <RefreshIcon />
              </IconButton>
              <IconButton onClick={() => setStockExpanded(!stockExpanded)} size="small">
                {stockExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
          }
        />
        <Collapse in={stockExpanded}>
          <CardContent sx={{ pt: 0 }}>
            {portfolio.positions.length === 0 ? (
              <Typography color="textSecondary" textAlign="center" py={3}>
                No stock positions found
              </Typography>
            ) : (
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Symbol</strong></TableCell>
                      <TableCell align="right"><strong>Shares</strong></TableCell>
                      <TableCell align="right"><strong>Avg Price</strong></TableCell>
                      <TableCell align="right"><strong>Current Price</strong></TableCell>
                      <TableCell align="right"><strong>Market Value</strong></TableCell>
                      <TableCell align="right"><strong>P&L</strong></TableCell>
                      <TableCell align="right"><strong>P&L %</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {portfolio.positions.map((position, index) => (
                      <TableRow key={`${position.symbol}-${index}`} hover>
                        <TableCell>
                          <Typography fontWeight="bold">{position.symbol}</Typography>
                        </TableCell>
                        <TableCell align="right">
                          {position.shares.toLocaleString()}
                        </TableCell>
                        <TableCell align="right">
                          {formatCurrency(position.avg_price)}
                        </TableCell>
                        <TableCell align="right">
                          {formatCurrency(position.current_price)}
                        </TableCell>
                        <TableCell align="right">
                          <Typography fontWeight="bold">
                            {formatCurrency(position.market_value)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Typography color={getPnLColor(position.pnl)} fontWeight="bold">
                            {formatCurrency(position.pnl)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Chip 
                            label={formatPercent(position.pnl_pct)}
                            color={position.pnl && position.pnl > 0 ? 'success' : 'error'}
                            variant="outlined"
                            size="small"
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Collapse>
      </Card>

      {/* Options Positions Table */}
      <Card>
        <CardHeader
          title={`Options Positions (${portfolio.option_positions.length})`}
          action={
            <Box>
              <IconButton onClick={fetchPortfolio} size="small">
                <RefreshIcon />
              </IconButton>
              <IconButton onClick={() => setOptionsExpanded(!optionsExpanded)} size="small">
                {optionsExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
          }
        />
        <Collapse in={optionsExpanded}>
          <CardContent sx={{ pt: 0 }}>
            {portfolio.option_positions.length === 0 ? (
              <Typography color="textSecondary" textAlign="center" py={3}>
                No options positions found
              </Typography>
            ) : (
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Contract</strong></TableCell>
                      <TableCell><strong>Underlying</strong></TableCell>
                      <TableCell align="center"><strong>Side</strong></TableCell>
                      <TableCell align="right"><strong>Quantity</strong></TableCell>
                      <TableCell align="right"><strong>Open Price</strong></TableCell>
                      <TableCell align="right"><strong>Current Price</strong></TableCell>
                      <TableCell align="right"><strong>P&L</strong></TableCell>
                      <TableCell align="right"><strong>P&L %</strong></TableCell>
                      <TableCell align="center"><strong>Status</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {portfolio.option_positions.map((position, index) => (
                      <TableRow key={`${position.contract_symbol}-${index}`} hover>
                        <TableCell>
                          <Typography variant="body2" fontFamily="monospace">
                            {position.contract_symbol}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography fontWeight="bold">{position.symbol}</Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Chip 
                            label={position.side}
                            color={position.side === 'long' ? 'primary' : 'secondary'}
                            size="small"
                          />
                        </TableCell>
                        <TableCell align="right">
                          {position.quantity}
                        </TableCell>
                        <TableCell align="right">
                          {formatCurrency(position.open_price)}
                        </TableCell>
                        <TableCell align="right">
                          {formatCurrency(position.current_price)}
                        </TableCell>
                        <TableCell align="right">
                          <Typography color={getPnLColor(position.pnl)} fontWeight="bold">
                            {formatCurrency(position.pnl)}
                          </Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Chip 
                            label={formatPercent(position.pnl_pct)}
                            color={position.pnl && position.pnl > 0 ? 'success' : 'error'}
                            variant="outlined"
                            size="small"
                          />
                        </TableCell>
                        <TableCell align="center">
                          <Chip 
                            label={position.status}
                            color={position.status === 'open' ? 'success' : 'default'}
                            size="small"
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Collapse>
      </Card>

      {/* Data freshness notice */}
      <Box mt={2}>
        <Typography variant="caption" color="textSecondary" textAlign="center" display="block">
          ⚠️ Using real Tradier API data - Positions and prices are live from your trading account
        </Typography>
      </Box>
    </Box>
  )
}
