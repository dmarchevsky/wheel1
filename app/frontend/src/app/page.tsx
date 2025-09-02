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
  Alert,
  Snackbar,
  Switch,
  FormControlLabel,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  AutoAwesome as AutoAwesomeIcon,
} from '@mui/icons-material'
import RecommendationsPanel from '@/components/RecommendationsPanel'
import { recommendationsApi } from '@/lib/api'

export default function Dashboard() {
  const [recommendationsExpanded, setRecommendationsExpanded] = useState(true)
  const [portfolioExpanded, setPortfolioExpanded] = useState(true)
  const [activityExpanded, setActivityExpanded] = useState(true)
  const [filtersVisible, setFiltersVisible] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [generationStatus, setGenerationStatus] = useState('idle')
  const [generationMessage, setGenerationMessage] = useState('')
  const [generationProgress, setGenerationProgress] = useState<any>(null)
  const [clearTrigger, setClearTrigger] = useState(0)
  const [metadata, setMetadata] = useState<any>(null)
  const [pollingEnabled, setPollingEnabled] = useState(false)
  const [pollingInterval, setPollingInterval] = useState(5)

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

  const handleMetadataUpdate = (newMetadata: any) => {
    setMetadata(newMetadata)
  }

  const formatTimestamp = (timestamp: string) => {
    if (!timestamp) return null
    const date = new Date(timestamp)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const handleGenerateRecommendations = async () => {
    try {
      console.log('🚀 Starting recommendation generation...')
      setGenerationStatus('pending')
      setGenerationMessage('Starting recommendation generation...')
      
      // Add a small delay to see the immediate feedback
      await new Promise(resolve => setTimeout(resolve, 200))
      
      const response = await recommendationsApi.generate()
      console.log('📋 Generation response:', response.data)
      const jobId = response.data.job_id
      
      if (!jobId) {
        throw new Error('No job ID received from server')
      }
      
      // Poll for job status
      const pollStatus = async () => {
        try {
          console.log(`🔍 Polling status for job ${jobId}`)
          const statusResponse = await recommendationsApi.getGenerationStatus(jobId)
          const job = statusResponse.data
          
          console.log('📊 Job status:', job)
          setGenerationStatus(job.status)
          
          // Store progress data
          setGenerationProgress(job)
          
          // Create detailed progress message
          let progressMessage = job.message || `Status: ${job.status}`
          if (job.status === 'running' && job.total_tickers > 0) {
            const processed = job.processed_tickers || 0
            const total = job.total_tickers || 0
            const generated = job.recommendations_generated || 0
            const currentTicker = job.current_ticker ? ` (${job.current_ticker})` : ''
            
            progressMessage = `Processing tickers: ${processed}/${total} | Recommendations: ${generated}${currentTicker}`
          }
          
          setGenerationMessage(progressMessage)
          
          if (job.status === 'pending' || job.status === 'running') {
            setTimeout(pollStatus, 2000) // Poll every 2 seconds
          } else if (job.status === 'completed') {
            setGenerationMessage(`✅ ${job.message || 'Generation completed successfully!'}`)
            // Refresh recommendations when generation is complete
            setTimeout(() => {
              setGenerationStatus('idle')
              setGenerationMessage('')
              // Trigger a refresh of recommendations
              window.location.reload() // Simple refresh for now
            }, 3000) // Show success for 3 seconds
          } else if (job.status === 'failed') {
            setGenerationMessage(`❌ ${job.message || 'Generation failed'}`)
            setTimeout(() => {
              setGenerationStatus('idle')
              setGenerationMessage('')
            }, 5000) // Show error for 5 seconds
          }
        } catch (error) {
          console.error('Error polling job status:', error)
          setGenerationStatus('failed')
          setGenerationMessage('❌ Error checking generation status')
          setTimeout(() => {
            setGenerationStatus('idle')
            setGenerationMessage('')
          }, 5000)
        }
      }
      
      // Start polling
      setTimeout(pollStatus, 1000) // First poll after 1 second
      
    } catch (error) {
      console.error('Error starting generation:', error)
      setGenerationStatus('failed')
      setGenerationMessage(`❌ Failed to start generation: ${error.message}`)
      setTimeout(() => {
        setGenerationStatus('idle')
        setGenerationMessage('')
      }, 5000)
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
              title={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Typography variant="h6">Latest Recommendations</Typography>
                  {metadata?.latest_update && (
                    <Typography variant="caption" color="textSecondary" sx={{ fontSize: '0.8rem' }}>
                      Updated: {formatTimestamp(metadata.latest_update)}
                    </Typography>
                  )}
                </Box>
              }
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
                    {generationStatus === 'pending' ? 'Starting...' : 
                     generationStatus === 'running' ? 'Generating...' : 
                     generationStatus === 'completed' ? 'Complete!' : 'Generate'}
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
                  {/* Auto-refresh controls */}
                  <FormControlLabel
                    control={
                      <Switch
                        size="small"
                        checked={pollingEnabled}
                        onChange={(e) => setPollingEnabled(e.target.checked)}
                      />
                    }
                    label="Auto"
                    sx={{ ml: 1 }}
                  />
                  {pollingEnabled && (
                    <FormControl size="small" sx={{ minWidth: 60 }}>
                      <Select
                        value={pollingInterval}
                        onChange={(e) => setPollingInterval(e.target.value as number)}
                        sx={{ '.MuiOutlinedInput-notchedOutline': { border: 'none' } }}
                      >
                        <MenuItem value={1}>1m</MenuItem>
                        <MenuItem value={2}>2m</MenuItem>
                        <MenuItem value={5}>5m</MenuItem>
                        <MenuItem value={10}>10m</MenuItem>
                        <MenuItem value={15}>15m</MenuItem>
                        <MenuItem value={30}>30m</MenuItem>
                      </Select>
                    </FormControl>
                  )}
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
                {/* Generation Status Alert */}
                {generationStatus !== 'idle' && (
                  <Alert 
                    severity={
                      generationStatus === 'completed' ? 'success' : 
                      generationStatus === 'failed' ? 'error' : 'info'
                    }
                    sx={{ mb: 2 }}
                  >
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {(generationStatus === 'pending' || generationStatus === 'running') && (
                          <CircularProgress size={16} />
                        )}
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {generationStatus === 'pending' ? 'Starting generation...' :
                           generationStatus === 'running' ? 'Generating recommendations...' :
                           generationStatus === 'completed' ? 'Generation completed!' :
                           generationStatus === 'failed' ? 'Generation failed' : 'Unknown status'}
                        </Typography>
                      </Box>
                      
                      {/* Detailed Progress for Running Status */}
                      {generationStatus === 'running' && generationProgress && (
                        <Box sx={{ mt: 1, p: 1, bgcolor: 'rgba(0,0,0,0.05)', borderRadius: 1 }}>
                          <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
                            <Box>
                              <Typography variant="caption" color="textSecondary">Total Tickers</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                {generationProgress.total_tickers || 0}
                              </Typography>
                            </Box>
                            <Box>
                              <Typography variant="caption" color="textSecondary">Processed</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                {generationProgress.processed_tickers || 0}
                              </Typography>
                            </Box>
                            <Box>
                              <Typography variant="caption" color="textSecondary">Recommendations</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                {generationProgress.recommendations_generated || 0}
                              </Typography>
                            </Box>
                            {generationProgress.current_ticker && (
                              <Box>
                                <Typography variant="caption" color="textSecondary">Current</Typography>
                                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                  {generationProgress.current_ticker}
                                </Typography>
                              </Box>
                            )}
                          </Box>
                        </Box>
                      )}
                      
                      {/* Completion Summary */}
                      {generationStatus === 'completed' && generationProgress && (
                        <Typography variant="caption" color="textSecondary">
                          Processed {generationProgress.processed_tickers || 0} tickers, 
                          generated {generationProgress.recommendations_generated || 0} recommendations
                        </Typography>
                      )}
                      
                      {/* Basic message for other states */}
                      {(generationStatus === 'pending' || generationStatus === 'failed') && (
                        <Typography variant="caption" color="textSecondary">
                          {generationMessage}
                        </Typography>
                      )}
                    </Box>
                  </Alert>
                )}
                
                <RecommendationsPanel 
                  onRefresh={handleRefresh}
                  onClearFilters={handleClearFilters}
                  onGenerateRecommendations={handleGenerateRecommendations}
                  refreshing={refreshing}
                  generationStatus={generationStatus}
                  filtersVisible={filtersVisible}
                  clearTrigger={clearTrigger}
                  onMetadataUpdate={handleMetadataUpdate}
                  pollingEnabled={pollingEnabled}
                  pollingInterval={pollingInterval}
                  onPollingEnabledChange={setPollingEnabled}
                  onPollingIntervalChange={setPollingInterval}
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
