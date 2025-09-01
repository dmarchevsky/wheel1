'use client'

import { useState, useEffect } from 'react'
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
} from '@mui/material'
import {
  TrendingUp as TrendingUpIcon,
  Close as CloseIcon,
  Info as InfoIcon,
  ShoppingCart as TradeIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material'
import { recommendationsApi } from '@/lib/api'
import { Recommendation } from '@/types'

interface RecommendationsPanelProps {
  maxRecommendations?: number
}

export default function RecommendationsPanel({ maxRecommendations = 5 }: RecommendationsPanelProps) {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchRecommendations = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await recommendationsApi.getCurrent()
      setRecommendations(response.data.slice(0, maxRecommendations))
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
  }, [maxRecommendations])

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
          <Grid container spacing={1}>
            {recommendations.map((recommendation) => (
              <Grid item xs={12} key={recommendation.id}>
                <Card variant="outlined" sx={{ position: 'relative', borderRadius: 0 }}>
                  <CardContent sx={{ p: 1.5, '&:last-child': { pb: 1.5 } }}>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      {/* Main Content Section */}
                      <Box sx={{ flex: 1 }}>
                        {/* Header Section */}
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flexWrap: 'wrap' }}>
                            <Typography variant="subtitle1" component="div" sx={{ fontWeight: 600, fontSize: '1rem' }}>
                              {recommendation.underlying_ticker || recommendation.symbol}
                        </Typography>
                            <Chip
                              label={recommendation.option_type?.toUpperCase() || 'PUT'}
                              size="small"
                              color="primary"
                              sx={{ borderRadius: 0, height: 20, fontSize: '0.7rem' }}
                            />
                        {recommendation.strike && (
                          <Chip
                                label={`$${recommendation.strike.toFixed(2)}`}
                            size="small"
                            variant="outlined"
                                sx={{ borderRadius: 0, height: 20, fontSize: '0.7rem' }}
                          />
                        )}
                        {recommendation.expiry && (
                          <Chip
                            label={formatExpiry(recommendation.expiry)}
                            size="small"
                            variant="outlined"
                            color="secondary"
                                sx={{ borderRadius: 0, height: 20, fontSize: '0.7rem' }}
                              />
                            )}
                          </Box>
                          

                        </Box>

                        {/* Key Financial Metrics in 2 rows */}
                        <Grid container spacing={1} sx={{ mb: 1 }}>
                          <Grid item xs={3} sm={2}>
                            <Typography variant="caption" color="textSecondary">Current</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.85rem' }}>
                              ${recommendation.current_price?.toFixed(2) || 'N/A'}
                            </Typography>
                          </Grid>
                          <Grid item xs={3} sm={2}>
                            <Typography variant="caption" color="textSecondary">Premium</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.85rem' }}>
                              ${recommendation.contract_price?.toFixed(2) || 'N/A'}
                            </Typography>
                          </Grid>
                          <Grid item xs={3} sm={2}>
                            <Typography variant="caption" color="textSecondary">Credit</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, color: 'success.main', fontSize: '0.85rem' }}>
                              ${recommendation.total_credit?.toFixed(0) || 'N/A'}
                            </Typography>
                          </Grid>
                          <Grid item xs={3} sm={2}>
                            <Typography variant="caption" color="textSecondary">Collateral</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.85rem' }}>
                              ${recommendation.collateral?.toFixed(0) || 'N/A'}
                            </Typography>
                          </Grid>
                          <Grid item xs={6} sm={2}>
                            <Typography variant="caption" color="textSecondary">Ann. ROI</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, color: 'success.main', fontSize: '0.85rem' }}>
                              {recommendation.annualized_roi ? `${recommendation.annualized_roi.toFixed(1)}%` : 'N/A'}
                            </Typography>
                          </Grid>
                          <Grid item xs={6} sm={2}>
                            <Typography variant="caption" color="textSecondary">Volume</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.85rem' }}>
                              {recommendation.volume?.toLocaleString() || 'N/A'}
                            </Typography>
                          </Grid>
                        </Grid>

                        {/* Company & Additional Info */}
                        <Grid container spacing={1} sx={{ mb: 1 }}>
                          <Grid item xs={4} sm={3}>
                            <Typography variant="caption" color="textSecondary">Sector</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                              {recommendation.sector || 'N/A'}
                            </Typography>
                          </Grid>
                          <Grid item xs={4} sm={3}>
                            <Typography variant="caption" color="textSecondary">Industry</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                              {recommendation.industry || 'N/A'}
                            </Typography>
                          </Grid>
                          <Grid item xs={4} sm={2}>
                            <Typography variant="caption" color="textSecondary">P/E</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                              {recommendation.pe_ratio ? recommendation.pe_ratio.toFixed(1) : 'N/A'}
                            </Typography>
                          </Grid>
                          <Grid item xs={6} sm={2}>
                            <Typography variant="caption" color="textSecondary">P/C Ratio</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                              {recommendation.put_call_ratio ? recommendation.put_call_ratio.toFixed(2) : 'N/A'}
                            </Typography>
                          </Grid>
                          <Grid item xs={6} sm={2}>
                            <Typography variant="caption" color="textSecondary">Earnings</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                              {recommendation.next_earnings_date ? 
                                new Date(recommendation.next_earnings_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'N/A'}
                            </Typography>
                          </Grid>
                        </Grid>

                        {/* Score Details */}
                        {recommendation.score_breakdown && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, flexWrap: 'wrap' }}>
                            {/* Overall Score at the beginning */}
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <Typography variant="caption" color="textSecondary">
                                Overall:
                              </Typography>
                              <Typography 
                                variant="body2" 
                                sx={{ 
                                  fontWeight: 600, 
                                  fontSize: '0.8rem',
                                  color: getScoreColor(recommendation.score) === 'success' ? 'success.main' : 
                                         getScoreColor(recommendation.score) === 'warning' ? 'warning.main' : 'error.main'
                                }}
                              >
                                {Math.round(recommendation.score * 100)}
                              </Typography>
                            </Box>
                            {Object.entries(recommendation.score_breakdown)
                              .filter(([key]) => !key.toLowerCase().includes('overall')) // Filter out any "Overall Score" entries
                              .map(([key, value]) => {
                              // Parse the value to get a number for color coding
                              const numericValue = parseFloat(value.toString().replace('%', '').replace('$', '').replace(',', ''));
                              let color = 'text.primary';
                              
                              // Color coding based on value ranges
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
                        )}
                        

                      </Box>
                      
                      {/* Vertical Button Section */}
                      <Box sx={{ 
                        display: 'flex', 
                        flexDirection: 'column', 
                        alignItems: 'center', 
                        gap: 1,
                        borderLeft: '1px solid',
                        borderColor: 'divider',
                        pl: 1,
                        minWidth: 48,
                        justifyContent: 'space-between'
                      }}>
                        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
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
                        <Typography 
                          variant="caption" 
                          color="textSecondary" 
                          sx={{ 
                            fontSize: '0.8rem',
                            textAlign: 'center',
                            lineHeight: 1
                          }}
                        >
                          {new Date(recommendation.created_at).toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric'
                          })}
                          <br />
                          {new Date(recommendation.created_at).toLocaleTimeString('en-US', { 
                            hour: '2-digit',
                            minute: '2-digit',
                            hour12: false
                          })}
                        </Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Box>
    </Box>
  )
}
