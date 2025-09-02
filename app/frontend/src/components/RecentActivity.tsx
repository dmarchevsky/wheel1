'use client'

import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Alert,
  CircularProgress,
  IconButton,
  Divider,
  useTheme,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  TrendingUp,
  TrendingDown,
  SwapHoriz,
  AccountBalance,
  AttachMoney,
  ShowChart,
} from '@mui/icons-material'
import { accountApi } from '@/lib/api'
import { ActivityEvent } from '@/types'

export default function RecentActivity() {
  const theme = useTheme()
  const [activities, setActivities] = useState<ActivityEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchActivity = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await accountApi.getActivity(7) // Last 7 days
      setActivities(response.data)
    } catch (err: any) {
      console.error('Error fetching activity:', err)
      setError(err.response?.data?.detail || 'Failed to fetch account activity')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchActivity()
  }, [])

  const formatCurrency = (value: number | undefined | null) => {
    if (value === undefined || value === null) return '$0.00'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value)
  }

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      const today = new Date()
      const yesterday = new Date(today)
      yesterday.setDate(yesterday.getDate() - 1)

      if (date.toDateString() === today.toDateString()) {
        return `Today ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
      } else if (date.toDateString() === yesterday.toDateString()) {
        return `Yesterday ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
      } else {
        return date.toLocaleDateString('en-US', { 
          month: 'short', 
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        })
      }
    } catch {
      return dateString
    }
  }

  const getActivityIcon = (type: string) => {
    const iconProps = { fontSize: 'small' as const }
    
    switch (type.toLowerCase()) {
      case 'buy':
        return <TrendingUp {...iconProps} />
      case 'sell':
        return <TrendingDown {...iconProps} />
      case 'trade':
      default:
        return <SwapHoriz {...iconProps} />
    }
  }

  const getActivityColor = (amount: number) => {
    if (amount > 0) return theme.palette.success.main
    if (amount < 0) return theme.palette.error.main
    return theme.palette.text.secondary
  }

  const getActivityTypeChipColor = (type: string): 'primary' | 'secondary' | 'success' | 'error' | 'warning' | 'info' => {
    switch (type.toLowerCase()) {
      case 'buy':
        return 'success'
      case 'sell':
        return 'error'
      case 'trade':
      default:
        return 'primary'
    }
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
        <IconButton onClick={fetchActivity} color="inherit" size="small">
          <RefreshIcon />
        </IconButton>
      }>
        {error}
      </Alert>
    )
  }

  if (activities.length === 0) {
    return (
      <Box textAlign="center" py={4}>
        <Typography color="textSecondary">
          No recent trades found. Stock and option trades from the last 7 days will appear here.
        </Typography>
        <IconButton onClick={fetchActivity} sx={{ mt: 2 }}>
          <RefreshIcon />
        </IconButton>
      </Box>
    )
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="body2" color="textSecondary">
          Last 7 days • {activities.length} trades
        </Typography>
        <IconButton onClick={fetchActivity} size="small">
          <RefreshIcon />
        </IconButton>
      </Box>

      <List disablePadding>
        {activities.slice(0, 10).map((activity, index) => (
          <React.Fragment key={`${activity.date}-${activity.type}-${index}`}>
            <ListItem 
              alignItems="flex-start" 
              sx={{ 
                px: 0,
                py: 1.5,
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.02)'
                }
              }}
            >
              <ListItemIcon sx={{ minWidth: 40, mt: 0.5 }}>
                {getActivityIcon(activity.type)}
              </ListItemIcon>
              
              <ListItemText
                primary={
                  <Box display="flex" alignItems="center" gap={1} mb={0.5}>
                    <Chip 
                      label={activity.type.toUpperCase()}
                      color={getActivityTypeChipColor(activity.type)}
                      size="small"
                      variant="filled"
                      sx={{ fontWeight: 'bold', minWidth: 50 }}
                    />
                    {activity.symbol && (
                      <Chip 
                        label={activity.symbol}
                        size="small"
                        variant="outlined"
                        color="primary"
                        sx={{ fontWeight: 'bold', fontSize: '0.75rem' }}
                      />
                    )}
                    <Typography 
                      variant="body2" 
                      sx={{ 
                        color: getActivityColor(activity.amount),
                        fontWeight: 600,
                        ml: 'auto'
                      }}
                    >
                      {activity.amount >= 0 ? '+' : ''}{formatCurrency(activity.amount)}
                    </Typography>
                  </Box>
                }
                secondary={
                  <Box>
                    <Typography variant="body2" color="textPrimary" gutterBottom>
                      {activity.description}
                    </Typography>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography variant="caption" color="textSecondary">
                        {formatDate(activity.date)}
                      </Typography>
                      {(activity.quantity || activity.price) && (
                        <Typography variant="caption" color="textSecondary">
                          {activity.quantity && `Qty: ${activity.quantity}`}
                          {activity.quantity && activity.price && ' • '}
                          {activity.price && `Price: ${formatCurrency(activity.price)}`}
                        </Typography>
                      )}
                    </Box>
                  </Box>
                }
              />
            </ListItem>
            {index < Math.min(activities.length - 1, 9) && (
              <Divider variant="inset" component="li" sx={{ ml: 5 }} />
            )}
          </React.Fragment>
        ))}
      </List>

      {activities.length > 10 && (
        <Box textAlign="center" mt={2}>
                  <Typography variant="body2" color="textSecondary">
          Showing 10 of {activities.length} recent trades
        </Typography>
        </Box>
      )}

      {/* Data source notice */}
      <Box mt={2}>
        <Typography variant="caption" color="textSecondary" textAlign="center" display="block">
          ⚠️ Real trading activity from Tradier API - Stock & option trades only
        </Typography>
      </Box>
    </Box>
  )
}
