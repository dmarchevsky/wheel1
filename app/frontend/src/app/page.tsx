'use client'

import {
  Box,
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Divider,
} from '@mui/material'
import {
  TrendingUp as TrendingUpIcon,
  AccountBalanceWallet as WalletIcon,
  ShowChart as ChartIcon,
} from '@mui/icons-material'
import RecommendationsPanel from '@/components/RecommendationsPanel'

export default function Dashboard() {
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
      


      {/* Main Content */}
      <Container maxWidth="xl" sx={{ flexGrow: 1, py: 2 }}>
        {/* Dashboard Grid Layout */}
        <Grid container spacing={3}>
          {/* Recommendations Panel */}
          <Grid item xs={12} md={6}>
            <RecommendationsPanel maxRecommendations={5} />
          </Grid>
          
          {/* Additional Dashboard Panels */}
          <Grid item xs={12} md={6}>
            <Card sx={{ borderRadius: 0 }}>
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
            <Card sx={{ borderRadius: 0 }}>
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
