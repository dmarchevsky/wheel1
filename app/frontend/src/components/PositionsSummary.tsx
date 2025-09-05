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
} from '@mui/icons-material'
import { accountApi } from '@/lib/api'
import { Position, OptionPosition } from '@/types'

interface PortfolioData {
  account_status?: any
  balances?: any
  positions?: Array<{
    symbol: string
    instrument_type: string
    quantity: number
    cost_basis: number
    current_price: number
    market_value: number
    pnl: number
    pnl_percent: number
    contract_symbol?: string
    option_type?: string
    strike?: number
    expiration?: string
    side?: string
  }>
  recent_orders?: any[]
  // Legacy format compatibility
  option_positions?: OptionPosition[]
}

export default function PositionsSummary() {
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
      console.log('Portfolio API response:', response.data) // Debug log
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
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
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

  // Separate positions by instrument type
  const allPositions = portfolio.positions || []
  const stockPositions = allPositions.filter(pos => pos.instrument_type === 'equity')
  const optionPositions = allPositions.filter(pos => pos.instrument_type === 'option')
  
  // Show only top 5 positions for dashboard summary
  const topStockPositions = stockPositions.slice(0, 5)
  const topOptionPositions = optionPositions.slice(0, 5)

  return (
    <Grid container spacing={3}>
      {/* Stock Positions Summary */}
      <Grid item xs={12} lg={6}>
        <Card>
          <CardHeader
            title={`Stock Positions (${stockPositions.length})`}
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
              {topStockPositions.length === 0 ? (
                <Typography color="textSecondary" textAlign="center" py={2}>
                  No stock positions found
                </Typography>
              ) : (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell><strong>Symbol</strong></TableCell>
                        <TableCell align="right"><strong>Shares</strong></TableCell>
                        <TableCell align="right"><strong>Current Price</strong></TableCell>
                        <TableCell align="right"><strong>Market Value</strong></TableCell>
                        <TableCell align="right"><strong>P&L %</strong></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {topStockPositions.map((position, index) => (
                        <TableRow key={`${position.symbol}-${index}`} hover>
                          <TableCell>
                            <Typography fontWeight="bold">{position.symbol}</Typography>
                          </TableCell>
                          <TableCell align="right">
                            {Math.abs(position.quantity).toLocaleString()}
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
                            <Chip 
                              label={formatPercent(position.pnl_percent)}
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
              {stockPositions.length > 5 && (
                <Box textAlign="center" mt={2}>
                  <Typography variant="body2" color="textSecondary">
                    Showing top 5 positions. <a href="/portfolio" style={{ color: theme.palette.primary.main }}>View all positions</a>
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Collapse>
        </Card>
      </Grid>

      {/* Options Positions Summary */}
      <Grid item xs={12} lg={6}>
        <Card>
          <CardHeader
            title={`Options Positions (${optionPositions.length})`}
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
              {topOptionPositions.length === 0 ? (
                <Typography color="textSecondary" textAlign="center" py={2}>
                  No options positions found
                </Typography>
              ) : (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell><strong>Contract</strong></TableCell>
                        <TableCell><strong>Underlying</strong></TableCell>
                        <TableCell align="center"><strong>Side</strong></TableCell>
                        <TableCell align="right"><strong>Qty</strong></TableCell>
                        <TableCell align="right"><strong>P&L %</strong></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {topOptionPositions.map((position, index) => (
                        <TableRow key={`${position.contract_symbol || position.symbol}-${index}`} hover>
                          <TableCell>
                            <Typography variant="body2" fontFamily="monospace" fontSize="0.75rem">
                              {position.contract_symbol && position.contract_symbol.length > 20 
                                ? `${position.contract_symbol.substring(0, 20)}...` 
                                : position.contract_symbol || position.symbol
                              }
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography fontWeight="bold">{position.symbol}</Typography>
                          </TableCell>
                          <TableCell align="center">
                            <Chip 
                              label={position.side || (position.quantity > 0 ? 'long' : 'short')}
                              color={position.side === 'long' || position.quantity > 0 ? 'primary' : 'secondary'}
                              size="small"
                            />
                          </TableCell>
                          <TableCell align="right">
                            {Math.abs(position.quantity)}
                          </TableCell>
                          <TableCell align="right">
                            <Chip 
                              label={formatPercent(position.pnl_percent)}
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
              {optionPositions.length > 5 && (
                <Box textAlign="center" mt={2}>
                  <Typography variant="body2" color="textSecondary">
                    Showing top 5 positions. <a href="/portfolio" style={{ color: theme.palette.primary.main }}>View all positions</a>
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Collapse>
        </Card>
      </Grid>
    </Grid>
  )
}
