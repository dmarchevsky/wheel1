'use client'

import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  LinearProgress,
  Button,
  Grid,
} from '@mui/material'
import {
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material'
import { Recommendation } from '@/types'

interface RecommendationCardProps {
  recommendation: Recommendation
  onExecute?: (recommendation: Recommendation) => void
}

export default function RecommendationCard({ recommendation, onExecute }: RecommendationCardProps) {
  const getRiskColor = (risk: string): 'success' | 'warning' | 'error' | 'default' => {
    switch (risk) {
      case 'Low':
        return 'success'
      case 'Medium':
        return 'warning'
      case 'High':
        return 'error'
      default:
        return 'default'
    }
  }

  const getRiskIcon = (risk: string) => {
    switch (risk) {
      case 'Low':
        return <CheckCircleIcon fontSize="small" />
      case 'Medium':
        return <WarningIcon fontSize="small" />
      case 'High':
        return <WarningIcon fontSize="small" />
      default:
        return undefined
    }
  }

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box>
            <Typography variant="h6" component="div">
              {recommendation.symbol}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              {recommendation.strategy} Strategy
            </Typography>
          </Box>
          <Chip
            icon={getRiskIcon(recommendation.risk)}
            label={recommendation.risk}
            color={getRiskColor(recommendation.risk)}
            variant="outlined"
            size="small"
            sx={{ minWidth: 'fit-content' }}
          />
        </Box>

        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={6}>
            <Typography variant="body2" color="textSecondary">
              Expected Return
            </Typography>
            <Typography variant="h6" color="success.main" sx={{ display: 'flex', alignItems: 'center' }}>
              <TrendingUpIcon sx={{ mr: 0.5, fontSize: '1rem' }} />
              {recommendation.expectedReturn}%
            </Typography>
          </Grid>
          <Grid item xs={6}>
            <Typography variant="body2" color="textSecondary">
              Confidence
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <LinearProgress
                variant="determinate"
                value={recommendation.confidence}
                sx={{ flexGrow: 1, mr: 1 }}
              />
              <Typography variant="body2">
                {recommendation.confidence}%
              </Typography>
            </Box>
          </Grid>
        </Grid>

        {recommendation.description && (
          <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
            {recommendation.description}
          </Typography>
        )}

        {recommendation.entryPrice && recommendation.targetPrice && (
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={4}>
              <Typography variant="body2" color="textSecondary">
                Entry
              </Typography>
              <Typography variant="body1">
                ${recommendation.entryPrice}
              </Typography>
            </Grid>
            <Grid item xs={4}>
              <Typography variant="body2" color="textSecondary">
                Target
              </Typography>
              <Typography variant="body1" color="success.main">
                ${recommendation.targetPrice}
              </Typography>
            </Grid>
            <Grid item xs={4}>
              <Typography variant="body2" color="textSecondary">
                Stop Loss
              </Typography>
              <Typography variant="body1" color="error.main">
                ${recommendation.stopLoss}
              </Typography>
            </Grid>
          </Grid>
        )}

        {onExecute && (
          <Button
            variant="contained"
            color="primary"
            fullWidth
            onClick={() => onExecute(recommendation)}
            sx={{ mt: 1 }}
          >
            Execute Trade
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
