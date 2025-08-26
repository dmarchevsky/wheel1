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
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Chip,
  LinearProgress,
  Alert,
} from '@mui/material'
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  TrendingUp as TrendingUpIcon,
  AccountBalance as AccountBalanceIcon,
  Settings as SettingsIcon,
  Refresh as RefreshIcon,
  TrendingDown as TrendingDownIcon,
  AttachMoney as MoneyIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material'
import { DataGrid, GridColDef } from '@mui/x-data-grid'

// Mock data for demonstration
const mockPositions = [
  {
    id: 1,
    symbol: 'AAPL',
    type: 'PUT',
    strike: 150,
    expiry: '2024-01-19',
    quantity: 1,
    avgPrice: 2.50,
    currentPrice: 2.75,
    pnl: 25.00,
    pnlPercent: 10.0,
  },
  {
    id: 2,
    symbol: 'TSLA',
    type: 'CALL',
    strike: 200,
    expiry: '2024-01-26',
    quantity: 2,
    avgPrice: 1.80,
    currentPrice: 1.60,
    pnl: -40.00,
    pnlPercent: -11.1,
  },
]

const mockRecommendations = [
  {
    id: 1,
    symbol: 'NVDA',
    strategy: 'Wheel',
    confidence: 85,
    expectedReturn: 12.5,
    risk: 'Medium',
  },
  {
    id: 2,
    symbol: 'AMD',
    strategy: 'Iron Condor',
    confidence: 72,
    expectedReturn: 8.3,
    risk: 'Low',
  },
]

const columns: GridColDef[] = [
  { field: 'symbol', headerName: 'Symbol', width: 100 },
  { field: 'type', headerName: 'Type', width: 80 },
  { field: 'strike', headerName: 'Strike', width: 100, type: 'number' },
  { field: 'expiry', headerName: 'Expiry', width: 120 },
  { field: 'quantity', headerName: 'Qty', width: 80, type: 'number' },
  { field: 'avgPrice', headerName: 'Avg Price', width: 120, type: 'number' },
  { field: 'currentPrice', headerName: 'Current', width: 120, type: 'number' },
  {
    field: 'pnl',
    headerName: 'P&L',
    width: 120,
    type: 'number',
    renderCell: (params) => (
      <Typography
        color={params.value >= 0 ? 'success.main' : 'error.main'}
        fontWeight="bold"
      >
        ${params.value.toFixed(2)}
      </Typography>
    ),
  },
  {
    field: 'pnlPercent',
    headerName: 'P&L %',
    width: 100,
    type: 'number',
    renderCell: (params) => (
      <Typography
        color={params.value >= 0 ? 'success.main' : 'error.main'}
        fontWeight="bold"
      >
        {params.value >= 0 ? '+' : ''}{params.value.toFixed(1)}%
      </Typography>
    ),
  },
]

export default function Dashboard() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [accountData, setAccountData] = useState<AccountBalance | null>(null)
  const [error, setError] = useState<string | null>(null)

  const fetchAccountData = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await accountApi.getAccountInfo()
      setAccountData(response.data)
    } catch (err) {
      console.error('Error fetching account data:', err)
      setError('Failed to fetch account data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAccountData()
  }, [])

  const handleRefresh = () => {
    fetchAccountData()
  }



  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* App Bar */}
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={() => setDrawerOpen(!drawerOpen)}
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Wheel Strategy Dashboard
          </Typography>
          <IconButton color="inherit" onClick={handleRefresh} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* Sidebar */}
      <Drawer
        variant="temporary"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        sx={{
          width: 240,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: 240,
            boxSizing: 'border-box',
          },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto' }}>
          <List>
            <ListItem button>
              <ListItemIcon>
                <DashboardIcon />
              </ListItemIcon>
              <ListItemText primary="Dashboard" />
            </ListItem>
            <ListItem button>
              <ListItemIcon>
                <TrendingUpIcon />
              </ListItemIcon>
              <ListItemText primary="Positions" />
            </ListItem>
            <ListItem button>
              <ListItemIcon>
                <AccountBalanceIcon />
              </ListItemIcon>
              <ListItemText primary="Account" />
            </ListItem>
            <Divider />
            <ListItem button>
              <ListItemIcon>
                <SettingsIcon />
              </ListItemIcon>
              <ListItemText primary="Settings" />
            </ListItem>
          </List>
        </Box>
      </Drawer>

      {/* Main Content */}
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        
        {loading && <LinearProgress sx={{ mb: 2 }} />}

        <Container maxWidth="xl">
          {/* Error Alert */}
          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {/* Summary Cards */}
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Account Number
                  </Typography>
                  <Typography variant="h6" component="div">
                    {accountData?.account_number || 'Loading...'}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Tradier Account
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Total Value
                  </Typography>
                  <Typography variant="h4" component="div">
                    ${accountData?.total_value?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Portfolio Value
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Available Cash
                  </Typography>
                  <Typography variant="h4" component="div">
                    ${accountData?.cash?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Ready to deploy
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} sm={6} md={3}>
              <Card>
                <CardContent>
                  <Typography color="textSecondary" gutterBottom>
                    Buying Power
                  </Typography>
                  <Typography variant="h4" component="div">
                    ${accountData?.buying_power?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Day Trade: ${accountData?.day_trade_buying_power?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00'}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Main Content Grid */}
          <Grid container spacing={3}>
            {/* Positions Table */}
            <Grid item xs={12} lg={8}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Current Positions
                  </Typography>
                  <Box sx={{ height: 400, width: '100%' }}>
                    <DataGrid
                      rows={mockPositions}
                      columns={columns}
                      initialState={{
                        pagination: {
                          paginationModel: { pageSize: 5 },
                        },
                      }}
                      pageSizeOptions={[5]}
                      disableRowSelectionOnClick
                      sx={{
                        '& .MuiDataGrid-cell': {
                          borderBottom: '1px solid #333',
                        },
                        '& .MuiDataGrid-columnHeaders': {
                          backgroundColor: '#1a1a1a',
                          borderBottom: '2px solid #333',
                        },
                      }}
                    />
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* Recommendations */}
            <Grid item xs={12} lg={4}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Recommendations
                  </Typography>
                  {mockRecommendations.map((rec) => (
                    <Box key={rec.id} sx={{ mb: 2, p: 2, border: '1px solid #333', borderRadius: 1 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="h6">{rec.symbol}</Typography>
                        <Chip 
                          label={rec.strategy} 
                          size="small" 
                          color="primary" 
                          variant="outlined"
                        />
                      </Box>
                      <Typography variant="body2" color="textSecondary" gutterBottom>
                        Expected Return: {rec.expectedReturn}%
                      </Typography>
                      <Typography variant="body2" color="textSecondary" gutterBottom>
                        Risk: {rec.risk}
                      </Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
                        <Typography variant="body2" sx={{ mr: 1 }}>
                          Confidence:
                        </Typography>
                        <LinearProgress 
                          variant="determinate" 
                          value={rec.confidence} 
                          sx={{ flexGrow: 1, mr: 1 }}
                        />
                        <Typography variant="body2">
                          {rec.confidence}%
                        </Typography>
                      </Box>
                    </Box>
                  ))}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Container>
      </Box>
    </Box>
  )
}
