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
      {/* Enhanced Header with Account Info */}
      <AppBar position="static" elevation={0} sx={{ background: 'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)' }}>
        <Toolbar sx={{ minHeight: '80px' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
            <AccountBalanceIcon sx={{ mr: 2, fontSize: 32 }} />
            <Box>
              <Typography variant="h5" component="div" sx={{ fontWeight: 600 }}>
                Wheel Strategy Dashboard
              </Typography>
              {accountData && (
                <Typography variant="body2" color="text.secondary">
                  Account: {accountData.account_number} • Last Updated: {accountData.last_updated ? formatDate(accountData.last_updated) : 'N/A'}
                </Typography>
              )}
            </Box>
          </Box>
          
          <IconButton 
            color="inherit" 
            onClick={handleRefresh} 
            disabled={loading}
            sx={{ 
              backgroundColor: 'rgba(255,255,255,0.1)', 
              '&:hover': { backgroundColor: 'rgba(255,255,255,0.2)' }
            }}
          >
            {loading ? <CircularProgress size={24} color="inherit" /> : <RefreshIcon />}
          </IconButton>
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

        {/* Enhanced Account Summary Cards */}
        {accountData && (
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ 
                background: 'linear-gradient(135deg, #00d4aa 0%, #00b894 100%)',
                color: 'white',
                height: '100%'
              }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <TrendingUpIcon sx={{ mr: 1 }} />
                    <Typography variant="h6" component="div">
                      Total Portfolio Value
                    </Typography>
                  </Box>
                  <Typography variant="h3" component="div" sx={{ fontWeight: 700, mb: 1 }}>
                    {formatCurrency(accountData.total_value)}
                  </Typography>
                  <Typography variant="body2" sx={{ opacity: 0.9 }}>
                    Account: {accountData.account_number}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ 
                background: 'linear-gradient(135deg, #3498db 0%, #2980b9 100%)',
                color: 'white',
                height: '100%'
              }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <WalletIcon sx={{ mr: 1 }} />
                    <Typography variant="h6" component="div">
                      Available Cash
                    </Typography>
                  </Box>
                  <Typography variant="h3" component="div" sx={{ fontWeight: 700, mb: 1 }}>
                    {formatCurrency(accountData.cash)}
                  </Typography>
                  <Typography variant="body2" sx={{ opacity: 0.9 }}>
                    Ready to deploy
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ 
                background: 'linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)',
                color: 'white',
                height: '100%'
              }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <ChartIcon sx={{ mr: 1 }} />
                    <Typography variant="h6" component="div">
                      Buying Power
                    </Typography>
                  </Box>
                  <Typography variant="h3" component="div" sx={{ fontWeight: 700, mb: 1 }}>
                    {formatCurrency(accountData.buying_power)}
                  </Typography>
                  <Typography variant="body2" sx={{ opacity: 0.9 }}>
                    Day Trade: {formatCurrency(accountData.day_trade_buying_power)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card sx={{ 
                background: 'linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%)',
                color: 'white',
                height: '100%'
              }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <AccountBalanceIcon sx={{ mr: 1 }} />
                    <Typography variant="h6" component="div">
                      Account Equity
                    </Typography>
                  </Box>
                  <Typography variant="h3" component="div" sx={{ fontWeight: 700, mb: 1 }}>
                    {formatCurrency(accountData.equity)}
                  </Typography>
                  <Typography variant="body2" sx={{ opacity: 0.9 }}>
                    Net Account Value
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Additional Account Details */}
        {accountData && (
          <Card sx={{ mb: 4 }}>
            <CardContent>
              <Typography variant="h6" component="div" sx={{ mb: 3 }}>
                Account Breakdown
              </Typography>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Stock Positions
                    </Typography>
                    <Typography variant="h6">
                      Long: {formatCurrency(accountData.long_stock_value)} | Short: {formatCurrency(accountData.short_stock_value)}
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Option Positions
                    </Typography>
                    <Typography variant="h6">
                      Long: {formatCurrency(accountData.long_option_value)} | Short: {formatCurrency(accountData.short_option_value)}
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
              <Divider sx={{ my: 2 }} />
              <Typography variant="body2" color="text.secondary">
                Data source: Tradier API • Last updated: {accountData.last_updated ? formatDate(accountData.last_updated) : 'N/A'}
              </Typography>
            </CardContent>
          </Card>
        )}

        {/* Placeholder for future content */}
        <Card>
          <CardContent>
            <Typography variant="h6" component="div" sx={{ mb: 2 }}>
              Dashboard Overview
            </Typography>
            <Typography color="textSecondary" align="center" sx={{ py: 8 }}>
              Additional dashboard components will be added here as the application evolves.
            </Typography>
          </CardContent>
        </Card>
      </Container>
    </Box>
  )
}
