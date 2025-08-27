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
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  Close as CloseIcon,
  Info as InfoIcon,
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
      <Card>
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
    <Card>
      <CardHeader
        title="Latest Recommendations"
        action={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Tooltip title="Refresh recommendations (may take up to 30 seconds)">
              <IconButton
                onClick={handleRefresh}
                disabled={refreshing}
                size="small"
              >
                {refreshing ? <CircularProgress size={20} /> : <RefreshIcon />}
              </IconButton>
            </Tooltip>
          </Box>
        }
      />
      
      {refreshing && <LinearProgress />}
      
      <CardContent>
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
            <Button
              variant="outlined"
              size="small"
              onClick={handleRefresh}
              disabled={refreshing}
              sx={{ mt: 1 }}
            >
              Generate Recommendations
            </Button>
          </Box>
        ) : (
          <Grid container spacing={2}>
            {recommendations.map((recommendation) => (
              <Grid item xs={12} key={recommendation.id}>
                <Card variant="outlined" sx={{ position: 'relative' }}>
                  <CardContent sx={{ pb: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
                          {recommendation.symbol}
                        </Typography>
                        {recommendation.strike && (
                          <Chip
                            label={`$${recommendation.strike}`}
                            size="small"
                            variant="outlined"
                          />
                        )}
                        {recommendation.expiry && (
                          <Chip
                            label={formatExpiry(recommendation.expiry)}
                            size="small"
                            variant="outlined"
                            color="secondary"
                          />
                        )}
                      </Box>
                      
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Chip
                          label={`${formatScore(recommendation.score)}%`}
                          color={getScoreColor(recommendation.score) as any}
                          size="small"
                          icon={<TrendingUpIcon />}
                        />
                        <Tooltip title="Dismiss recommendation">
                          <IconButton
                            size="small"
                            onClick={() => handleDismiss(recommendation.id)}
                          >
                            <CloseIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </Box>
                    
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" color="textSecondary">
                        {formatDate(recommendation.created_at)}
                      </Typography>
                      
                      {recommendation.rationale && (
                        <Tooltip title="View details">
                          <IconButton size="small">
                            <InfoIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </CardContent>
    </Card>
  )
}
