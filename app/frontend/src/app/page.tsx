'use client'

import { useState, useEffect } from 'react'
import { accountApi } from '@/lib/api'
import { AccountBalance } from '@/types'
import {
  Box,
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  AppBar,
  Toolbar,
  IconButton,
  Alert,
  LinearProgress,
  CircularProgress,
  Divider,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  AccountBalance as AccountBalanceIcon,
  TrendingUp as TrendingUpIcon,
  AccountBalanceWallet as WalletIcon,
  ShowChart as ChartIcon,
} from '@mui/icons-material'
import RecommendationsPanel from '@/components/RecommendationsPanel'

export default function Dashboard() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Account data
  const [accountData, setAccountData] = useState<AccountBalance | null>(null)

  const fetchAllData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Fetch account data only
      const accountRes = await accountApi.getAccountInfo()
      setAccountData(accountRes.data)
      
    } catch (err) {
      console.error('Error fetching account data:', err)
      setError('Failed to fetch account data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAllData()
  }, [])

  const handleRefresh = () => {
    fetchAllData()
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <style jsx global>{`
        @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.5; }
          100% { opacity: 1; }
        }
      `}</style>
      {/* Header with Account Balances */}
      <AppBar position="static" elevation={0} sx={{ background: 'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)' }}>
        <Toolbar sx={{ minHeight: '60px', py: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
            <AccountBalanceIcon sx={{ mr: 1.5, fontSize: 24 }} />
            <Typography variant="h6" component="div" sx={{ fontWeight: 600, mr: 3 }}>
              Wheel Strategy Dashboard
            </Typography>
            {accountData && (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Total:
                  </Typography>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    {formatCurrency(accountData.total_value)}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Cash:
                  </Typography>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    {formatCurrency(accountData.cash)}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Equity:
                  </Typography>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    {formatCurrency(accountData.equity)}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Buying Power:
                  </Typography>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    {formatCurrency(accountData.buying_power)}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    Day Trade:
                  </Typography>
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    {formatCurrency(accountData.day_trade_buying_power)}
                  </Typography>
                </Box>
              </Box>
            )}
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <IconButton 
              color="inherit" 
              onClick={handleRefresh} 
              disabled={loading}
              size="small"
              sx={{ 
                backgroundColor: 'rgba(255,255,255,0.1)', 
                '&:hover': { backgroundColor: 'rgba(255,255,255,0.2)' }
              }}
            >
              {loading ? <CircularProgress size={20} color="inherit" /> : <RefreshIcon />}
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Container maxWidth="xl" sx={{ flexGrow: 1, py: 4 }}>
        {loading && <LinearProgress sx={{ mb: 3 }} />}
        
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Dashboard Grid Layout */}
        <Grid container spacing={3}>
          {/* Recommendations Panel */}
          <Grid item xs={12} md={6}>
            <RecommendationsPanel maxRecommendations={5} />
          </Grid>
          
          {/* Additional Dashboard Panels */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" component="div" sx={{ mb: 2 }}>
                  Portfolio Summary
                </Typography>
                <Typography color="textSecondary" align="center" sx={{ py: 8 }}>
                  Portfolio performance and analytics will be displayed here.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          {/* Recent Activity */}
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" component="div" sx={{ mb: 2 }}>
                  Recent Activity
                </Typography>
                <Typography color="textSecondary" align="center" sx={{ py: 8 }}>
                  Recent trades and position changes will be displayed here.
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Container>
    </Box>
  )
}
