'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Grid,
  Paper,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Divider,
  IconButton,
  Tooltip,
  Switch,
  FormControlLabel,
  Card,
  CardContent,
} from '@mui/material'
import {
  Close as CloseIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Info as InfoIcon,
  Warning as WarningIcon,
} from '@mui/icons-material'
import { marketDataApi } from '@/lib/api'

interface TradeModalProps {
  open: boolean
  onClose: () => void
  recommendation: any
}

interface OptionQuote {
  symbol: string
  description: string
  option_type: string
  strike: number
  expiration_date: string
  bid: number
  ask: number
  last: number
  change: number
  volume: number
  open_interest: number
  bid_size: number
  ask_size: number
  greeks: {
    delta?: number
    gamma?: number
    theta?: number
    vega?: number
    bid_iv?: number
    mid_iv?: number
    ask_iv?: number
  }
}

interface UnderlyingQuote {
  symbol: string
  last: number
  change: number
  change_percentage: number
  bid: number
  ask: number
  volume: number
}

const TradeModal: React.FC<TradeModalProps> = ({ open, onClose, recommendation }) => {
  const [underlyingQuote, setUnderlyingQuote] = useState<UnderlyingQuote | null>(null)
  const [optionQuotes, setOptionQuotes] = useState<OptionQuote[]>([])
  const [selectedOption, setSelectedOption] = useState<OptionQuote | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Trading parameters
  const [quantity, setQuantity] = useState(1)
  const [orderType, setOrderType] = useState('limit')
  const [limitPrice, setLimitPrice] = useState('')
  const [duration, setDuration] = useState('day')
  const [previewMode, setPreviewMode] = useState(true)
  
  // Calculated values
  const [totalCredit, setTotalCredit] = useState(0)
  const [collateralRequired, setCollateralRequired] = useState(0)
  const [maxProfit, setMaxProfit] = useState(0)
  const [maxLoss, setMaxLoss] = useState(0)
  const [breakeven, setBreakeven] = useState(0)

  const fetchMarketData = useCallback(async () => {
    if (!recommendation || !open) return
    
    setLoading(true)
    setError(null)
    
    try {
      // Fetch underlying quote
      const underlyingResponse = await marketDataApi.getQuote(recommendation.symbol)
      setUnderlyingQuote(underlyingResponse.data.quote)
      
      // Fetch option quotes for the recommended expiration
      const optionsResponse = await marketDataApi.getOptionQuotes(
        recommendation.symbol,
        recommendation.expiry
      )
      
      // Filter for put options around the recommended strike
      const putOptions = optionsResponse.data.options
        .filter((opt: OptionQuote) => opt.option_type.toLowerCase() === 'put')
        .sort((a: OptionQuote, b: OptionQuote) => Math.abs(a.strike - recommendation.strike) - Math.abs(b.strike - recommendation.strike))
      
      setOptionQuotes(putOptions)
      
      // Pre-select the recommended option if available
      const recommendedOption = putOptions.find((opt: OptionQuote) => 
        Math.abs(opt.strike - recommendation.strike) < 0.01
      )
      
      if (recommendedOption) {
        setSelectedOption(recommendedOption)
        setLimitPrice(recommendedOption.bid.toString())
      }
      
    } catch (err: any) {
      console.error('Error fetching market data:', err)
      setError('Failed to fetch real-time market data. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [recommendation, open])

  useEffect(() => {
    if (open && recommendation) {
      fetchMarketData()
    }
  }, [open, recommendation, fetchMarketData])

  // Calculate trade metrics when parameters change
  useEffect(() => {
    if (selectedOption && quantity && limitPrice) {
      const credit = parseFloat(limitPrice) * quantity * 100 // Options are per contract (100 shares)
      const collateral = selectedOption.strike * quantity * 100
      const profit = credit
      const loss = collateral - credit
      const breakeven = selectedOption.strike - parseFloat(limitPrice)
      
      setTotalCredit(credit)
      setCollateralRequired(collateral)
      setMaxProfit(profit)
      setMaxLoss(loss)
      setBreakeven(breakeven)
    }
  }, [selectedOption, quantity, limitPrice])

  const handleOptionSelect = (option: OptionQuote) => {
    setSelectedOption(option)
    setLimitPrice(option.bid.toString()) // Default to bid price for selling
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value)
  }

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(2)}%`
  }

  const getMoneyness = (strike: number, underlying: number) => {
    const ratio = strike / underlying
    if (ratio > 1.05) return { label: 'OTM', color: 'error' as const }
    if (ratio > 0.95) return { label: 'ATM', color: 'warning' as const }
    return { label: 'ITM', color: 'success' as const }
  }

  const handleSubmitTrade = () => {
    // This is disabled for now as requested
    alert('Trade submission is currently disabled. This is a preview-only interface.')
  }

  if (!recommendation) return null

  return (
    <Dialog 
      open={open} 
      onClose={onClose} 
      maxWidth="lg" 
      fullWidth
      PaperProps={{
        sx: { minHeight: '80vh' }
      }}
    >
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pb: 1 }}>
        <Box>
          <Typography variant="h6" component="span">
            Trade Options - {recommendation.symbol}
          </Typography>
          {underlyingQuote && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
              <Typography variant="body2" color="textSecondary">
                {formatCurrency(underlyingQuote.last)}
              </Typography>
              <Chip
                size="small"
                icon={underlyingQuote.change >= 0 ? <TrendingUpIcon /> : <TrendingDownIcon />}
                label={`${underlyingQuote.change >= 0 ? '+' : ''}${underlyingQuote.change.toFixed(2)} (${underlyingQuote.change_percentage?.toFixed(2)}%)`}
                color={underlyingQuote.change >= 0 ? 'success' : 'error'}
                variant="outlined"
              />
            </Box>
          )}
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Refresh market data">
            <IconButton onClick={fetchMarketData} disabled={loading}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <IconButton onClick={onClose}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Grid container spacing={3}>
          {/* Option Chain */}
          <Grid item xs={12} lg={7}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Put Options Chain - {recommendation.expiry}
              </Typography>
              
              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : (
                <TableContainer sx={{ maxHeight: 400 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell>Strike</TableCell>
                        <TableCell>Bid</TableCell>
                        <TableCell>Ask</TableCell>
                        <TableCell>Last</TableCell>
                        <TableCell>Volume</TableCell>
                        <TableCell>OI</TableCell>
                        <TableCell>IV</TableCell>
                        <TableCell>Delta</TableCell>
                        <TableCell>Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {optionQuotes.map((option) => {
                        const isSelected = selectedOption?.symbol === option.symbol
                        const moneyness = underlyingQuote ? getMoneyness(option.strike, underlyingQuote.last) : null
                        const isRecommended = Math.abs(option.strike - recommendation.strike) < 0.01
                        
                        return (
                          <TableRow
                            key={option.symbol}
                            hover
                            selected={isSelected}
                            onClick={() => handleOptionSelect(option)}
                            sx={{ 
                              cursor: 'pointer',
                              backgroundColor: isRecommended ? 'action.selected' : undefined
                            }}
                          >
                            <TableCell>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <Typography variant="body2" fontWeight={isRecommended ? 'bold' : 'normal'}>
                                  ${option.strike}
                                </Typography>
                                {isRecommended && (
                                  <Chip label="Recommended" size="small" color="primary" variant="outlined" />
                                )}
                              </Box>
                            </TableCell>
                            <TableCell>${option.bid.toFixed(2)}</TableCell>
                            <TableCell>${option.ask.toFixed(2)}</TableCell>
                            <TableCell>${option.last.toFixed(2)}</TableCell>
                            <TableCell>{option.volume.toLocaleString()}</TableCell>
                            <TableCell>{option.open_interest.toLocaleString()}</TableCell>
                            <TableCell>{option.greeks.mid_iv ? formatPercent(option.greeks.mid_iv) : '-'}</TableCell>
                            <TableCell>{option.greeks.delta ? option.greeks.delta.toFixed(3) : '-'}</TableCell>
                            <TableCell>
                              {moneyness && (
                                <Chip label={moneyness.label} size="small" color={moneyness.color} variant="outlined" />
                              )}
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Paper>
          </Grid>

          {/* Trade Panel */}
          <Grid item xs={12} lg={5}>
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="h6" gutterBottom>
                Order Entry
              </Typography>

              {selectedOption && (
                <Box sx={{ mb: 2, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
                  <Typography variant="subtitle2" color="primary">
                    Selected Option
                  </Typography>
                  <Typography variant="body2">
                    {selectedOption.description}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
                    <Typography variant="caption">
                      Bid: ${selectedOption.bid.toFixed(2)}
                    </Typography>
                    <Typography variant="caption">
                      Ask: ${selectedOption.ask.toFixed(2)}
                    </Typography>
                    <Typography variant="caption">
                      Last: ${selectedOption.last.toFixed(2)}
                    </Typography>
                  </Box>
                </Box>
              )}

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Quantity"
                    type="number"
                    value={quantity}
                    onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                    inputProps={{ min: 1 }}
                  />
                </Grid>
                <Grid item xs={6}>
                  <FormControl fullWidth>
                    <InputLabel>Order Type</InputLabel>
                    <Select
                      value={orderType}
                      label="Order Type"
                      onChange={(e) => setOrderType(e.target.value)}
                    >
                      <MenuItem value="limit">Limit</MenuItem>
                      <MenuItem value="market">Market</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>

                {orderType === 'limit' && (
                  <Grid item xs={6}>
                    <TextField
                      fullWidth
                      label="Limit Price"
                      type="number"
                      value={limitPrice}
                      onChange={(e) => setLimitPrice(e.target.value)}
                      inputProps={{ step: 0.01, min: 0 }}
                    />
                  </Grid>
                )}

                <Grid item xs={6}>
                  <FormControl fullWidth>
                    <InputLabel>Duration</InputLabel>
                    <Select
                      value={duration}
                      label="Duration"
                      onChange={(e) => setDuration(e.target.value)}
                    >
                      <MenuItem value="day">Day</MenuItem>
                      <MenuItem value="gtc">Good Till Canceled</MenuItem>
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>

              <FormControlLabel
                control={
                  <Switch
                    checked={previewMode}
                    onChange={(e) => setPreviewMode(e.target.checked)}
                  />
                }
                label="Preview Mode (Trade submission disabled)"
                sx={{ mt: 2 }}
              />
            </Paper>

            {/* Trade Summary */}
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Trade Summary
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={6}>
                  <Card variant="outlined">
                    <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Typography variant="caption" color="textSecondary">
                        Total Credit
                      </Typography>
                      <Typography variant="h6" color="success.main">
                        {formatCurrency(totalCredit)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card variant="outlined">
                    <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Typography variant="caption" color="textSecondary">
                        Collateral Required
                      </Typography>
                      <Typography variant="h6">
                        {formatCurrency(collateralRequired)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card variant="outlined">
                    <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Typography variant="caption" color="textSecondary">
                        Max Profit
                      </Typography>
                      <Typography variant="h6" color="success.main">
                        {formatCurrency(maxProfit)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card variant="outlined">
                    <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Typography variant="caption" color="textSecondary">
                        Max Loss
                      </Typography>
                      <Typography variant="h6" color="error.main">
                        {formatCurrency(maxLoss)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12}>
                  <Card variant="outlined">
                    <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Typography variant="caption" color="textSecondary">
                        Breakeven Point
                      </Typography>
                      <Typography variant="h6">
                        ${breakeven.toFixed(2)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              {selectedOption && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  <Typography variant="caption">
                    <strong>Strategy:</strong> Sell {quantity} {selectedOption.option_type.toUpperCase()} option{quantity > 1 ? 's' : ''} 
                    at ${selectedOption.strike} strike. Profit if {recommendation.symbol} stays above ${breakeven.toFixed(2)} at expiration.
                  </Typography>
                </Alert>
              )}
            </Paper>
          </Grid>
        </Grid>
      </DialogContent>

      <DialogActions sx={{ justifyContent: 'space-between', px: 3, pb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningIcon color="warning" fontSize="small" />
          <Typography variant="caption" color="textSecondary">
            Real Tradier API data • Trade submission currently disabled
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSubmitTrade}
            disabled={!selectedOption || !limitPrice || previewMode}
            color="primary"
          >
            Submit Trade (Disabled)
          </Button>
        </Box>
      </DialogActions>
    </Dialog>
  )
}

export default TradeModal
