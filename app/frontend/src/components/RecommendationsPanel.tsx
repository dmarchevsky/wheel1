'use client'

import React, { useState, useEffect } from 'react'
import {
  Card,
  CardContent,
  CardHeader,
  Typography,
  Box,
  Chip,
  Button,
  IconButton,
  Alert,
  Skeleton,
  Grid,
  Tooltip,
  LinearProgress,
  CircularProgress,
  TableContainer,
  Paper,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
} from '@mui/material'
import {
  TrendingUp as TrendingUpIcon,
  Close as CloseIcon,
  Info as InfoIcon,
  ShoppingCart as TradeIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material'
import { recommendationsApi } from '@/lib/api'
import { Recommendation } from '@/types'

interface RecommendationsPanelProps {
  refreshRef?: React.MutableRefObject<(() => Promise<void>) | null>
}

export default function RecommendationsPanel({ refreshRef }: RecommendationsPanelProps) {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedRows, setExpandedRows] = useState<{ [key: number]: boolean }>({})

  const fetchRecommendations = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await recommendationsApi.getCurrent()
      setRecommendations(response.data)
    } catch (err: any) {
      console.error('Error fetching recommendations:', err)
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Request timed out. The server is taking too long to respond.')
      } else if (err.response?.status === 500) {
        setError('Server error. Please try again later.')
      } else {
        setError('Failed to fetch recommendations')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    try {
      setRefreshing(true)
      setError(null)
      await recommendationsApi.refresh()
      await fetchRecommendations()
    } catch (err: any) {
      console.error('Error refreshing recommendations:', err)
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Refresh timed out. This operation can take up to 30 seconds.')
      } else if (err.response?.status === 500) {
        setError('Server error during refresh. Please try again later.')
      } else {
        setError('Failed to refresh recommendations')
      }
    } finally {
      setRefreshing(false)
    }
  }

  const handleDismiss = async (recommendationId: number) => {
    try {
      await recommendationsApi.dismiss(recommendationId.toString())
      // Remove from local state
      setRecommendations(prev => prev.filter(rec => rec.id !== recommendationId))
    } catch (err) {
      console.error('Error dismissing recommendation:', err)
    }
  }

  const handleTrade = (recommendation: Recommendation) => {
    // TODO: Implement trade functionality
    console.log('Trade clicked for:', recommendation)
    // This could open a trade modal, navigate to a trade page, etc.
  }

  useEffect(() => {
    fetchRecommendations()
    
    // Set up refresh ref for parent component
    if (refreshRef) {
      refreshRef.current = handleRefresh
    }
  }, [])

  const formatScore = (score: number) => {
    return (score * 100).toFixed(1)
  }

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'success'
    if (score >= 0.6) return 'warning'
    return 'error'
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatExpiry = (expiryString: string) => {
    if (!expiryString) return 'N/A'
    const expiry = new Date(expiryString)
    const now = new Date()
    const daysToExpiry = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
    return `${daysToExpiry}d`
  }

  if (loading) {
    return (
      <Card sx={{ borderRadius: 0 }}>
        <CardHeader
          title="Latest Recommendations"
          action={
            <Skeleton variant="circular" width={40} height={40} />
          }
        />
        <CardContent>
          <Grid container spacing={2}>
            {[...Array(3)].map((_, index) => (
              <Grid item xs={12} key={index}>
                <Skeleton variant="rectangular" height={80} />
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>
    )
  }

  return (
    <Box>
      {refreshing && <LinearProgress sx={{ mb: 2 }} />}
      
      <Box>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {recommendations.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography color="textSecondary" variant="body2">
              No recommendations available
            </Typography>
          </Box>
                ) : (
          <TableContainer component={Paper} sx={{ borderRadius: 0 }}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ 
                  backgroundColor: 'background.paper',
                  borderBottom: '2px solid',
                  borderColor: 'divider'
                }}>
                  <TableCell sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5,
                    width: 40
                  }}></TableCell>
                  <TableCell sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5
                  }}>Symbol</TableCell>
                  <TableCell sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5
                  }}>Type</TableCell>
                  <TableCell sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5
                  }}>Strike</TableCell>
                  <TableCell sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5
                  }}>Expiry</TableCell>
                  <TableCell sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5
                  }}>Current</TableCell>
                  <TableCell sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5
                  }}>Credit</TableCell>
                  <TableCell sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5
                  }}>ROI</TableCell>
                  <TableCell sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5
                  }}>Score</TableCell>
                  <TableCell sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5
                  }}>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {recommendations.map((recommendation) => (
                  <React.Fragment key={recommendation.id}>
                    <TableRow 
                      sx={{ 
                        '&:hover': { 
                          backgroundColor: 'action.hover',
                          transition: 'background-color 0.2s ease-in-out'
                        },
                        '& td': { 
                          borderBottom: '1px solid',
                          borderColor: 'divider',
                          py: 1.5
                        }
                      }}
                    >
                      {/* Expand/Collapse */}
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => setExpandedRows(prev => ({
                            ...prev,
                            [recommendation.id]: !prev[recommendation.id]
                          }))}
                          sx={{ p: 0.5 }}
                        >
                          {expandedRows[recommendation.id] ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                        </IconButton>
                      </TableCell>

                      {/* Symbol */}
                      <TableCell>
                        <Box>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {recommendation.underlying_ticker || recommendation.symbol}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            {recommendation.name || 'N/A'}
                          </Typography>
                        </Box>
                      </TableCell>

                      {/* Option Type */}
                      <TableCell>
                        <Chip
                          label={recommendation.option_type?.toUpperCase() || 'PUT'}
                          size="small"
                          color="primary"
                          sx={{ borderRadius: 0, height: 20, fontSize: '0.7rem' }}
                        />
                      </TableCell>

                      {/* Strike */}
                      <TableCell>
                        <Typography variant="body2">
                          {recommendation.strike ? `$${recommendation.strike.toFixed(2)}` : 'N/A'}
                        </Typography>
                      </TableCell>

                      {/* Expiry */}
                      <TableCell>
                        <Typography variant="body2">
                          {recommendation.expiry ? formatExpiry(recommendation.expiry) : 'N/A'}
                        </Typography>
                      </TableCell>

                      {/* Current Price */}
                      <TableCell>
                        <Typography variant="body2">
                          {recommendation.current_price ? `$${recommendation.current_price.toFixed(2)}` : 'N/A'}
                        </Typography>
                      </TableCell>

                      {/* Credit */}
                      <TableCell>
                        <Typography variant="body2" sx={{ color: 'success.main', fontWeight: 500 }}>
                          {recommendation.total_credit ? `$${recommendation.total_credit.toFixed(0)}` : 'N/A'}
                        </Typography>
                      </TableCell>

                      {/* ROI */}
                      <TableCell>
                        <Typography variant="body2" sx={{ color: 'success.main', fontWeight: 500 }}>
                          {recommendation.annualized_roi ? `${recommendation.annualized_roi.toFixed(1)}%` : 'N/A'}
                        </Typography>
                      </TableCell>

                      {/* Score */}
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Typography 
                            variant="body2" 
                            sx={{ 
                              fontWeight: 600,
                              color: getScoreColor(recommendation.score) === 'success' ? 'success.main' : 
                                     getScoreColor(recommendation.score) === 'warning' ? 'warning.main' : 'error.main'
                            }}
                          >
                            {Math.round(recommendation.score * 100)}
                          </Typography>
                        </Box>
                      </TableCell>

                      {/* Actions */}
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                          <Tooltip title="Trade this option">
                            <IconButton
                              size="small"
                              color="primary"
                              onClick={() => handleTrade(recommendation)}
                              sx={{ p: 0.5 }}
                            >
                              <TradeIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Dismiss recommendation">
                            <IconButton
                              size="small"
                              onClick={() => handleDismiss(recommendation.id)}
                              sx={{ p: 0.5 }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>

                    {/* Expanded Card View */}
                    {expandedRows[recommendation.id] && (
                      <TableRow>
                        <TableCell colSpan={10} sx={{ p: 0, border: 0 }}>
                          <Card variant="outlined" sx={{ m: 1, borderRadius: 0 }}>
                            <CardContent sx={{ p: 2 }}>
                              <Grid container spacing={2}>
                                {/* Key Financial Metrics */}
                                <Grid item xs={12} md={6}>
                                  <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
                                    Financial Metrics
                                  </Typography>
                                  <Grid container spacing={1}>
                                    <Grid item xs={6}>
                                      <Typography variant="caption" color="textSecondary">Premium</Typography>
                                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                        {recommendation.contract_price ? `$${recommendation.contract_price.toFixed(2)}` : 'N/A'}
                                      </Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                      <Typography variant="caption" color="textSecondary">Collateral</Typography>
                                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                        {recommendation.collateral ? `$${recommendation.collateral.toFixed(0)}` : 'N/A'}
                                      </Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                      <Typography variant="caption" color="textSecondary">Volume</Typography>
                                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                        {recommendation.volume ? recommendation.volume.toLocaleString() : 'N/A'}
                                      </Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                      <Typography variant="caption" color="textSecondary">Created</Typography>
                                      <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                                        {formatDate(recommendation.created_at)}
                                      </Typography>
                                    </Grid>
                                  </Grid>
                                </Grid>

                                {/* Company Information */}
                                <Grid item xs={12} md={6}>
                                  <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
                                    Company Details
                                  </Typography>
                                  <Grid container spacing={1}>
                                    <Grid item xs={6}>
                                      <Typography variant="caption" color="textSecondary">Sector</Typography>
                                      <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                                        {recommendation.sector || 'N/A'}
                                      </Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                      <Typography variant="caption" color="textSecondary">Industry</Typography>
                                      <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                                        {recommendation.industry || 'N/A'}
                                      </Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                      <Typography variant="caption" color="textSecondary">P/E Ratio</Typography>
                                      <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                                        {recommendation.pe_ratio ? recommendation.pe_ratio.toFixed(1) : 'N/A'}
                                      </Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                      <Typography variant="caption" color="textSecondary">P/C Ratio</Typography>
                                      <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                                        {recommendation.put_call_ratio ? recommendation.put_call_ratio.toFixed(2) : 'N/A'}
                                      </Typography>
                                    </Grid>
                                    <Grid item xs={6}>
                                      <Typography variant="caption" color="textSecondary">Earnings</Typography>
                                      <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                                        {recommendation.next_earnings_date ? 
                                          new Date(recommendation.next_earnings_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'N/A'}
                                      </Typography>
                                    </Grid>
                                  </Grid>
                                </Grid>

                                {/* Score Breakdown */}
                                {recommendation.score_breakdown && (
                                  <Grid item xs={12}>
                                    <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
                                      Score Breakdown
                                    </Typography>
                                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                                      {Object.entries(recommendation.score_breakdown)
                                        .filter(([key]) => !key.toLowerCase().includes('overall'))
                                        .map(([key, value]) => {
                                          const numericValue = parseFloat(value.toString().replace('%', '').replace('$', '').replace(',', ''));
                                          let color = 'text.primary';
                                          
                                          if (key.toLowerCase().includes('yield') || key.toLowerCase().includes('roi')) {
                                            color = numericValue > 20 ? 'success.main' : numericValue > 10 ? 'warning.main' : 'error.main';
                                          } else if (key.toLowerCase().includes('score') || key.toLowerCase().includes('probability')) {
                                            color = numericValue > 70 ? 'success.main' : numericValue > 50 ? 'warning.main' : 'error.main';
                                          } else if (key.toLowerCase().includes('ratio') || key.toLowerCase().includes('volume')) {
                                            color = numericValue > 1000 ? 'success.main' : numericValue > 500 ? 'warning.main' : 'error.main';
                                          }
                                          
                                          return (
                                            <Box key={key} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                              <Typography variant="caption" color="textSecondary">
                                                {key}:
                                              </Typography>
                                              <Typography 
                                                variant="body2" 
                                                sx={{ 
                                                  fontWeight: 500, 
                                                  fontSize: '0.8rem',
                                                  color: color
                                                }}
                                              >
                                                {value}
                                              </Typography>
                                            </Box>
                                          );
                                        })}
                                    </Box>
                                  </Grid>
                                )}
                              </Grid>
                            </CardContent>
                          </Card>
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Box>
    </Box>
  )
}
