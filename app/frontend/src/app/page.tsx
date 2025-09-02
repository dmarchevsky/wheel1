'use client'

import React, { useState, useRef } from 'react'
import {
  Box,
  Container,
  Card,
  CardHeader,
  CardContent,
  Typography,
  IconButton,
  Collapse,
  Button,
  CircularProgress,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  AutoAwesome as AutoAwesomeIcon,
} from '@mui/icons-material'
import RecommendationsPanel from '@/components/RecommendationsPanel'

export default function Dashboard() {
  const [recommendationsExpanded, setRecommendationsExpanded] = useState(true)
  const [portfolioExpanded, setPortfolioExpanded] = useState(true)
  const [activityExpanded, setActivityExpanded] = useState(true)
  const [filtersVisible, setFiltersVisible] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [generationStatus, setGenerationStatus] = useState('idle')
  const [clearTrigger, setClearTrigger] = useState(0)
  const generateRef = useRef<(() => Promise<void>) | null>(null)

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      // The actual refresh logic is handled by the RecommendationsPanel
      // We just manage the loading state here
      await new Promise(resolve => setTimeout(resolve, 100)) // Small delay to show loading state
    } finally {
      setRefreshing(false)
    }
  }

  const handleClearFilters = () => {
    setClearTrigger(prev => prev + 1)
  }

  const handleGenerateRecommendations = async () => {
    if (generateRef.current) {
      setGenerationStatus('pending')
      try {
        await generateRef.current()
      } catch (error) {
        setGenerationStatus('failed')
      }
    }
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
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                  <Button
                    variant={filtersVisible ? "contained" : "outlined"}
                    onClick={() => setFiltersVisible(!filtersVisible)}
                    size="small"
                    startIcon={<FilterIcon />}
                  >
                    Filters
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={handleClearFilters}
                    size="small"
                    disabled={!filtersVisible}
                  >
                    Clear
                  </Button>
                  <Button
                    variant="contained"
                    color="primary"
                    onClick={handleGenerateRecommendations}
                    disabled={generationStatus === 'pending' || generationStatus === 'running'}
                    startIcon={generationStatus === 'pending' || generationStatus === 'running' ? 
                      <CircularProgress size={16} /> : <AutoAwesomeIcon />}
                    size="small"
                  >
                    Generate
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={handleRefresh}
                    disabled={refreshing}
                    startIcon={refreshing ? <CircularProgress size={16} /> : <RefreshIcon />}
                    size="small"
                  >
                    Refresh
                  </Button>
                  <IconButton
                    onClick={() => setRecommendationsExpanded(!recommendationsExpanded)}
                    sx={{ borderRadius: 0 }}
                  >
                    {recommendationsExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                  </IconButton>
                </Box>
              }
            />
            <Collapse in={recommendationsExpanded}>
              <CardContent sx={{ pt: 0 }}>
                <RecommendationsPanel 
                  onRefresh={handleRefresh}
                  onClearFilters={handleClearFilters}
                  onGenerateRecommendations={handleGenerateRecommendations}
                  refreshing={refreshing}
                  generationStatus={generationStatus}
                  filtersVisible={filtersVisible}
                  clearTrigger={clearTrigger}
                />
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
