'use client'

import { useState } from 'react'
import {
  Box,
  Container,
  Card,
  CardContent,
  CardHeader,
  Typography,
  IconButton,
  Collapse,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material'
import RecommendationsPanel from '@/components/RecommendationsPanel'

export default function Dashboard() {
  const [recommendationsExpanded, setRecommendationsExpanded] = useState(true)
  const [portfolioExpanded, setPortfolioExpanded] = useState(true)
  const [activityExpanded, setActivityExpanded] = useState(true)

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
        {/* Dashboard Sections */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* Recommendations Panel */}
          <Card sx={{ borderRadius: 0 }}>
            <CardHeader
              title="Latest Recommendations"
              action={
                <IconButton
                  onClick={() => setRecommendationsExpanded(!recommendationsExpanded)}
                  sx={{ borderRadius: 0 }}
                >
                  {recommendationsExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              }
            />
            <Collapse in={recommendationsExpanded}>
              <CardContent sx={{ pt: 0 }}>
                <RecommendationsPanel maxRecommendations={5} />
              </CardContent>
            </Collapse>
          </Card>
          
          {/* Portfolio Summary */}
          <Card sx={{ borderRadius: 0 }}>
            <CardHeader
              title="Portfolio Summary"
              action={
                <IconButton
                  onClick={() => setPortfolioExpanded(!portfolioExpanded)}
                  sx={{ borderRadius: 0 }}
                >
                  {portfolioExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              }
            />
            <Collapse in={portfolioExpanded}>
              <CardContent sx={{ pt: 0 }}>
                <Typography color="textSecondary" align="center" sx={{ py: 8 }}>
                  Portfolio performance and analytics will be displayed here.
                </Typography>
              </CardContent>
            </Collapse>
          </Card>
          
          {/* Recent Activity */}
          <Card sx={{ borderRadius: 0 }}>
            <CardHeader
              title="Recent Activity"
              action={
                <IconButton
                  onClick={() => setActivityExpanded(!activityExpanded)}
                  sx={{ borderRadius: 0 }}
                >
                  {activityExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                </IconButton>
              }
            />
            <Collapse in={activityExpanded}>
              <CardContent sx={{ pt: 0 }}>
                <Typography color="textSecondary" align="center" sx={{ py: 8 }}>
                  Recent trades and position changes will be displayed here.
                </Typography>
              </CardContent>
            </Collapse>
          </Card>
        </Box>
      </Container>
    </Box>
  )
}
