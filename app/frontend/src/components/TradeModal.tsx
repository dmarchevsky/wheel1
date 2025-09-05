'use client'

import React, { useState, useEffect, useCallback, useRef } from 'react'
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
import { useThemeContext } from '@/contexts/ThemeContext'
import { marketDataApi, accountApi } from '@/lib/api'

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
  const { environment } = useThemeContext()
  const [underlyingQuote, setUnderlyingQuote] = useState<UnderlyingQuote | null>(null)
  const [optionQuotes, setOptionQuotes] = useState<OptionQuote[]>([])
  const [selectedOption, setSelectedOption] = useState<OptionQuote | null>(null)
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Trading parameters
  const [quantity, setQuantity] = useState(1)
  const [orderType, setOrderType] = useState('limit')
  const [limitPrice, setLimitPrice] = useState('')
  const [duration, setDuration] = useState('day')
  
  // Calculated values
  const [totalCredit, setTotalCredit] = useState(0)
  const [collateralRequired, setCollateralRequired] = useState(0)
  const [maxProfit, setMaxProfit] = useState(0)
  const [maxLoss, setMaxLoss] = useState(0)
  const [breakeven, setBreakeven] = useState(0)
  
  // Ref for scrolling to recommended option
  const recommendedOptionRef = useRef<HTMLDivElement>(null)

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
      
      // Filter for put options and sort by strike price for better usability
      const putOptions = optionsResponse.data.options
        .filter((opt: OptionQuote) => opt.option_type.toLowerCase() === 'put')
        .sort((a: OptionQuote, b: OptionQuote) => a.strike - b.strike) // Sort by strike price first
      
      setOptionQuotes(putOptions)
      
      // Pre-select the recommended option if available
      const recommendedOption = putOptions.find((opt: OptionQuote) => 
        Math.abs(opt.strike - recommendation.strike) < 0.01
      )
      
      if (recommendedOption) {
        setSelectedOption(recommendedOption)
        setLimitPrice(recommendedOption.bid.toString())
        
        // Scroll to the recommended option after a short delay to ensure DOM is updated
        setTimeout(() => {
          if (recommendedOptionRef.current) {
            recommendedOptionRef.current.scrollIntoView({ 
              behavior: 'smooth', 
              block: 'center' 
            })
          }
        }, 100)
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

  const getMoneyness = (strike: number, underlying: number, optionType: string) => {
    // For PUT options: Lower strike = more ITM, Higher strike = more OTM
    // For CALL options: Higher strike = more ITM, Lower strike = more OTM
    
    if (!underlying || underlying <= 0) {
      return { label: 'N/A', color: 'default' as const }
    }
    
    const ratio = strike / underlying
    const optionTypeLower = optionType.toLowerCase()
    
    if (optionTypeLower === 'put') {
      // PUT options: strike > underlying = ITM, strike < underlying = OTM
      // For sellers: OTM puts (low strike) are safer, ITM puts (high strike) are riskier
      if (ratio > 1.03) return { label: 'ITM', color: 'error' as const }        // Strike > 103% of underlying (risky for sellers)
      if (ratio > 0.97) return { label: 'ATM', color: 'warning' as const }      // Strike 97-103% of underlying
      return { label: 'OTM', color: 'success' as const }                        // Strike < 97% of underlying (safe for sellers)
    } else if (optionTypeLower === 'call') {
      // CALL options: strike < underlying = ITM, strike > underlying = OTM  
      // For sellers: OTM calls (high strike) are safer, ITM calls (low strike) are riskier
      if (ratio < 0.97) return { label: 'ITM', color: 'error' as const }        // Strike < 97% of underlying (risky for sellers)
      if (ratio < 1.03) return { label: 'ATM', color: 'warning' as const }      // Strike 97-103% of underlying
      return { label: 'OTM', color: 'success' as const }                        // Strike > 103% of underlying (safe for sellers)
    } else {
      // Unknown option type
      return { label: 'N/A', color: 'default' as const }
    }
  }

  const handleSubmitTrade = async () => {
    if (!selectedOption || !limitPrice) {
      setError('Please select an option and enter a limit price.')
      return
    }

    const environmentName = environment === 'production' ? 'LIVE MODE' : 'SANDBOX MODE'
    const isProduction = environment === 'production'
    
    const confirmationMessage = isProduction 
      ? `⚠️ WARNING: You are about to submit a REAL TRADE in LIVE MODE!\n\n` +
        `Symbol: ${selectedOption.symbol}\n` +
        `Strike: $${selectedOption.strike}\n` +
        `Quantity: ${quantity}\n` +
        `Limit Price: $${limitPrice}\n` +
        `Total Value: $${(parseFloat(limitPrice) * quantity * 100).toFixed(2)}\n\n` +
        `This will execute a real trade with real money. Are you sure?`
      : `Trade submission in ${environmentName}:\n\n` +
        `Symbol: ${selectedOption.symbol}\n` +
        `Strike: $${selectedOption.strike}\n` +
        `Quantity: ${quantity}\n` +
        `Limit Price: $${limitPrice}\n` +
        `Total Value: $${(parseFloat(limitPrice) * quantity * 100).toFixed(2)}\n\n` +
        `This trade will be submitted to your ${environmentName.toLowerCase()}.`

    if (!confirm(confirmationMessage)) {
      return
    }

    setSubmitting(true)
    setError(null)

    try {
      const orderData = {
        symbol: selectedOption.description.split(' ')[0], // Extract underlying symbol
        side: "sell_to_open", // For cash-secured puts
        quantity,
        order_type: orderType,
        price: orderType === 'limit' ? parseFloat(limitPrice) : undefined,
        duration,
        option_symbol: selectedOption.symbol
      }

      const response = await accountApi.submitOrder(orderData)
      
      if (response.data) {
        const { order_id, environment: responseEnv } = response.data
        
        alert(
          `✅ Order submitted successfully!\n\n` +
          `Environment: ${responseEnv.toUpperCase()}\n` +
          `Order ID: ${order_id}\n\n` +
          `You can check the status in your ${responseEnv === 'production' ? 'live' : 'sandbox'} Tradier account.`
        )
        
        // Close modal on successful submission
        onClose()
      }
    } catch (err: any) {
      console.error('Error submitting trade:', err)
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to submit trade'
      setError(`Trade submission failed: ${errorMessage}`)
    } finally {
      setSubmitting(false)
    }
  }

  if (!recommendation) return null

  return (
    <Dialog 
      open={open} 
      onClose={onClose} 
      maxWidth="lg" 
      fullWidth
      PaperProps={{
        sx: { minHeight: '80vh', borderRadius: 0 }
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
                sx={{ borderRadius: 0 }}
              />
            </Box>
          )}
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Refresh market data">
            <span>
              <IconButton onClick={fetchMarketData} disabled={loading} sx={{ borderRadius: 0 }}>
                <RefreshIcon />
              </IconButton>
            </span>
          </Tooltip>
          <IconButton onClick={onClose} sx={{ borderRadius: 0 }}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2, borderRadius: 0 }}>
            {error}
          </Alert>
        )}

        <Grid container spacing={3}>
          {/* Option Chain */}
          <Grid item xs={12} lg={8}>
            <Paper sx={{ p: 2, borderRadius: 0 }}>
              <Typography variant="h6" gutterBottom>
                Put Options Chain - {recommendation.expiry}
              </Typography>
              
              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : (
                <TableContainer sx={{ height: 200, overflowX: 'hidden', width: '100%' }}>
                  <Table size="small" stickyHeader sx={{ minWidth: 0, tableLayout: 'fixed' }} padding="checkbox">
                                        <TableHead>
                      <TableRow>
                        <TableCell sx={{ width: '15%', minWidth: 70, fontSize: '0.75rem' }}>Strike</TableCell>
                        <TableCell sx={{ width: '12%', minWidth: 55, fontSize: '0.75rem' }}>Bid</TableCell>
                        <TableCell sx={{ width: '12%', minWidth: 55, fontSize: '0.75rem' }}>Ask</TableCell>
                        <TableCell sx={{ width: '12%', minWidth: 55, fontSize: '0.75rem' }}>Last</TableCell>
                        <TableCell sx={{ width: '10%', minWidth: 50, fontSize: '0.75rem' }}>Delta</TableCell>
                        <TableCell sx={{ width: '10%', minWidth: 50, fontSize: '0.75rem' }}>Volume</TableCell>
                        <TableCell sx={{ width: '10%', minWidth: 50, fontSize: '0.75rem' }}>OI</TableCell>
                        <TableCell sx={{ width: '10%', minWidth: 50, fontSize: '0.75rem' }}>IV</TableCell>
                        <TableCell sx={{ width: '9%', minWidth: 45, fontSize: '0.75rem' }}>Status</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {optionQuotes.map((option) => {
                        const isSelected = selectedOption?.symbol === option.symbol
                        const moneyness = underlyingQuote ? getMoneyness(option.strike, underlyingQuote.last, option.option_type) : null
                        const isRecommended = Math.abs(option.strike - recommendation.strike) < 0.01
                        
                        return (
                          <TableRow
                            key={option.symbol}
                            ref={isRecommended ? recommendedOptionRef : undefined}
                            hover
                            selected={isSelected}
                            onClick={() => handleOptionSelect(option)}
                            sx={{ 
                              cursor: 'pointer',
                              backgroundColor: isRecommended ? 'primary.50' : undefined,
                              borderLeft: isRecommended ? '4px solid' : undefined,
                              borderLeftColor: isRecommended ? 'primary.main' : undefined,
                              '&:hover': {
                                backgroundColor: isRecommended ? 'primary.100' : 'action.hover'
                              }
                            }}
                          >
                            <TableCell sx={{ fontSize: '0.75rem' }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                {isRecommended && (
                                  <Box
                                    sx={{
                                      width: 8,
                                      height: 8,
                                      borderRadius: '50%',
                                      backgroundColor: 'primary.main',
                                      flexShrink: 0
                                    }}
                                  />
                                )}
                                <Typography variant="body2" fontWeight={isRecommended ? 'bold' : 'normal'} sx={{ fontSize: '0.75rem' }}>
                                  ${option.strike}
                                </Typography>
                              </Box>
                            </TableCell>
                            <TableCell sx={{ fontSize: '0.75rem' }}>${option.bid.toFixed(2)}</TableCell>
                            <TableCell sx={{ fontSize: '0.75rem' }}>${option.ask.toFixed(2)}</TableCell>
                            <TableCell sx={{ fontSize: '0.75rem' }}>${option.last.toFixed(2)}</TableCell>
                            <TableCell sx={{ fontSize: '0.75rem' }}>
                              {option.greeks.delta ? option.greeks.delta.toFixed(3) : '-'}
                            </TableCell>
                            <TableCell sx={{ fontSize: '0.75rem' }}>{option.volume.toLocaleString()}</TableCell>
                            <TableCell sx={{ fontSize: '0.75rem' }}>{option.open_interest.toLocaleString()}</TableCell>
                            <TableCell sx={{ fontSize: '0.75rem' }}>
                              {option.greeks.mid_iv ? formatPercent(option.greeks.mid_iv) : '-'}
                            </TableCell>
                            <TableCell sx={{ fontSize: '0.75rem' }}>
                              {moneyness && (
                                <Tooltip title={`Strike: $${option.strike} | Underlying: $${underlyingQuote?.last?.toFixed(2)} | Ratio: ${(option.strike / (underlyingQuote?.last || 1)).toFixed(3)}`}>
                                  <Chip label={moneyness.label} size="small" color={moneyness.color} variant="outlined" sx={{ borderRadius: 0 }} />
                                </Tooltip>
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

          {/* Score Breakdown */}
          <Grid item xs={12} lg={4}>
            <Paper sx={{ p: 2, borderRadius: 0 }}>
              <Typography variant="h6" gutterBottom>
                Score Breakdown
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0, height: 200, overflowY: 'auto' }}>
                {Object.entries(recommendation.score_breakdown).map(([key, value]) => (
                  <Box 
                    key={key} 
                    sx={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center',
                      py: 0.5,
                      px: 1,
                      borderBottom: '1px solid',
                      borderColor: 'divider',
                      '&:last-child': { borderBottom: 'none' }
                    }}
                  >
                    <Typography variant="body2" sx={{ fontSize: '0.75rem', color: 'text.secondary' }}>
                      {key}
                    </Typography>
                    <Typography variant="body2" fontWeight="bold" sx={{ fontSize: '0.75rem' }}>
                      {value}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Paper>
          </Grid>
        </Grid>

        {/* Order Entry and Trade Summary - Moved below option chains */}
        <Grid container spacing={3} sx={{ mt: 2 }}>
          {/* Order Entry */}
          <Grid item xs={12} lg={6}>
            <Paper sx={{ p: 1.5, borderRadius: 0 }}>
              <Typography variant="h6" gutterBottom sx={{ mb: 1.5 }}>
                Order Entry
              </Typography>
              


              {selectedOption && (
                <Box sx={{ mb: 1.5, p: 1.5, bgcolor: 'background.default' }}>
                  <Typography variant="subtitle2" color="primary" sx={{ fontSize: '0.875rem' }}>
                    Selected Option
                  </Typography>
                  <Typography variant="body2" sx={{ fontSize: '0.75rem', mt: 0.5 }}>
                    {selectedOption.description}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1.5, mt: 1 }}>
                    <Typography variant="caption" sx={{ fontSize: '0.7rem' }}>
                      Bid: ${selectedOption.bid.toFixed(2)}
                    </Typography>
                    <Typography variant="caption" sx={{ fontSize: '0.7rem' }}>
                      Ask: ${selectedOption.ask.toFixed(2)}
                    </Typography>
                    <Typography variant="caption" sx={{ fontSize: '0.7rem' }}>
                      Last: ${selectedOption.last.toFixed(2)}
                    </Typography>
                  </Box>
                </Box>
              )}

              <Grid container spacing={1.5}>
                <Grid item xs={6}>
                  <TextField
                    fullWidth
                    label="Quantity"
                    type="number"
                    value={quantity}
                    onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                    inputProps={{ min: 1 }}
                    size="small"
                  />
                </Grid>
                <Grid item xs={6}>
                  <FormControl fullWidth size="small">
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
                      size="small"
                    />
                  </Grid>
                )}

                <Grid item xs={6}>
                  <FormControl fullWidth size="small">
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


            </Paper>
          </Grid>

          {/* Trade Summary */}
          <Grid item xs={12} lg={6}>
            <Paper sx={{ p: 1.5, borderRadius: 0 }}>
              <Typography variant="h6" gutterBottom sx={{ mb: 1.5 }}>
                Trade Summary
              </Typography>

              <Grid container spacing={1.5}>
                <Grid item xs={6}>
                  <Card variant="outlined" sx={{ borderColor: 'success.main', bgcolor: 'success.50', borderRadius: 0 }}>
                    <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
                      <Typography variant="caption" color="textSecondary" sx={{ fontSize: '0.7rem' }}>
                        Total Credit
                      </Typography>
                      <Typography variant="h6" color="success.main" sx={{ fontSize: '1rem', mt: 0.5 }}>
                        {formatCurrency(totalCredit)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card variant="outlined" sx={{ borderColor: 'warning.main', bgcolor: 'warning.50', borderRadius: 0 }}>
                    <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
                      <Typography variant="caption" color="textSecondary" sx={{ fontSize: '0.7rem' }}>
                        Collateral Required
                      </Typography>
                      <Typography variant="h6" color="warning.main" sx={{ fontSize: '1rem', mt: 0.5 }}>
                        {formatCurrency(collateralRequired)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card variant="outlined" sx={{ borderRadius: 0 }}>
                    <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
                      <Typography variant="caption" color="textSecondary" sx={{ fontSize: '0.7rem' }}>
                        Max Profit
                      </Typography>
                      <Typography variant="h6" color="success.main" sx={{ fontSize: '1rem', mt: 0.5 }}>
                        {formatCurrency(maxProfit)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={6}>
                  <Card variant="outlined" sx={{ borderRadius: 0 }}>
                    <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
                      <Typography variant="caption" color="textSecondary" sx={{ fontSize: '0.7rem' }}>
                        Max Loss
                      </Typography>
                      <Typography variant="h6" color="error.main" sx={{ fontSize: '1rem', mt: 0.5 }}>
                        {formatCurrency(maxLoss)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                <Grid item xs={12}>
                  <Card variant="outlined" sx={{ borderRadius: 0 }}>
                    <CardContent sx={{ p: 1, '&:last-child': { pb: 1 } }}>
                      <Typography variant="caption" color="textSecondary" sx={{ fontSize: '0.7rem' }}>
                        Breakeven Point
                      </Typography>
                      <Typography variant="h6" sx={{ fontSize: '1rem', mt: 0.5 }}>
                        ${breakeven.toFixed(2)}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>

              {selectedOption && (
                <Alert severity="info" sx={{ mt: 2, borderRadius: 0 }}>
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
            Mode: {environment === 'production' ? 'Live Mode' : 'Sandbox Mode'} • 
            {environment === 'production' ? ' Real trades will be executed' : ' Paper trading - no real trades'}
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button onClick={onClose} sx={{ borderRadius: 0 }}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSubmitTrade}
            disabled={!selectedOption || !limitPrice || submitting}
            color="primary"
            sx={{ borderRadius: 0 }}
            startIcon={submitting ? <CircularProgress size={16} /> : undefined}
          >
            {submitting ? 'Submitting...' : 'Submit Trade'}
          </Button>
        </Box>
      </DialogActions>
    </Dialog>
  )
}

export default TradeModal
