'use client'

import {
  Card,
  CardContent,
  Typography,
  Box,
  Skeleton,
} from '@mui/material'
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
} from '@mui/icons-material'

interface SummaryCardProps {
  title: string
  value: string | number
  subtitle?: string
  change?: {
    value: number
    percent: number
  }
  loading?: boolean
  color?: 'primary' | 'success' | 'error' | 'warning' | 'info'
}

export default function SummaryCard({ 
  title, 
  value, 
  subtitle, 
  change, 
  loading = false,
  color = 'primary'
}: SummaryCardProps) {
  if (loading) {
    return (
      <Card>
        <CardContent>
          <Skeleton variant="text" width="60%" height={24} />
          <Skeleton variant="text" width="40%" height={32} />
          {subtitle && <Skeleton variant="text" width="80%" height={20} />}
        </CardContent>
      </Card>
    )
  }

  const isPositive = change && change.value >= 0
  const showChange = change !== undefined

  return (
    <Card>
      <CardContent>
        <Typography color="textSecondary" gutterBottom variant="body2">
          {title}
        </Typography>
        
        <Typography 
          variant="h4" 
          component="div" 
          color={showChange ? (isPositive ? 'success.main' : 'error.main') : 'text.primary'}
          sx={{ 
            display: 'flex', 
            alignItems: 'center',
            mb: subtitle ? 1 : 0
          }}
        >
          {showChange && (
            isPositive ? 
              <TrendingUpIcon sx={{ mr: 1, fontSize: '1.5rem' }} /> : 
              <TrendingDownIcon sx={{ mr: 1, fontSize: '1.5rem' }} />
          )}
          {typeof value === 'number' && value >= 0 ? `$${value.toLocaleString()}` : value}
        </Typography>
        
        {subtitle && (
          <Typography variant="body2" color="textSecondary">
            {subtitle}
          </Typography>
        )}
        
        {showChange && (
          <Box sx={{ mt: 1 }}>
            <Typography 
              variant="body2" 
              color={isPositive ? 'success.main' : 'error.main'}
              sx={{ display: 'flex', alignItems: 'center' }}
            >
              {isPositive ? '+' : ''}{change.value >= 0 ? '$' : '-$'}{Math.abs(change.value).toLocaleString()} 
              ({isPositive ? '+' : ''}{change.percent.toFixed(1)}%)
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  )
}

