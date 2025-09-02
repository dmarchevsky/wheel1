'use client'

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  IconButton,
  Tooltip,
  LinearProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Grid,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Switch,
  FormControlLabel,
  Divider,
  Badge,
  CircularProgress,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Refresh as RefreshIcon,
  Schedule as ScheduleIcon,
  ShoppingCart as TradeIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material'
import { recommendationsApi } from '@/lib/api'

interface FilterOptions {
  score_range: { min: number; max: number };
  roi_range: { min: number; max: number };
  max_collateral: number;
}

interface Filters {
  symbol: string;
  option_type: string;
  score_range: [number, number];
  roi_range: [number, number];
  max_collateral: number;
}

interface SortConfig {
  field: string;
  direction: 'asc' | 'desc';
}

interface RecommendationsPanelProps {
  onRefresh?: () => void;
  onClearFilters?: () => void;
  onGenerateRecommendations?: () => void;
  refreshing?: boolean;
  generationStatus?: string;
  filtersVisible?: boolean;
  clearTrigger?: number;
  onMetadataUpdate?: (metadata: any) => void;
}

export default function RecommendationsPanel({ 
  onRefresh, 
  onClearFilters,
  onGenerateRecommendations,
  refreshing: externalRefreshing,
  generationStatus: externalGenerationStatus,
  filtersVisible = false,
  clearTrigger = 0,
  onMetadataUpdate
}: RecommendationsPanelProps) {
  const [recommendations, setRecommendations] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const actualRefreshing = externalRefreshing !== undefined ? externalRefreshing : refreshing
  const [error, setError] = useState<string | null>(null)
  const [expandedRows, setExpandedRows] = useState<{ [key: number]: boolean }>({})
  
  // Filtering and sorting state
  const [filters, setFilters] = useState<Filters>({
    symbol: '',
    option_type: '',
    score_range: [0, 1],
    roi_range: [0, 100],
    max_collateral: 100000,
  })
  
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: 'score',
    direction: 'desc'
  })
  
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    score_range: { min: 0, max: 1 },
    roi_range: { min: 0, max: 100 },
    max_collateral: 100000,
  })
  
  // Polling state
  const [pollingEnabled, setPollingEnabled] = useState(false)
  const [pollingInterval, setPollingInterval] = useState(5) // minutes
  const [lastPollTime, setLastPollTime] = useState<Date | null>(null)
  
  // Use external generation status only (no internal state)
  const actualGenerationStatus = externalGenerationStatus || 'idle'

  const fetchRecommendations = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Fetch all recommendations - filtering will be done on frontend
      const params = {
        limit: 100,
      }
      
      const [recommendationsResponse, metadataResponse] = await Promise.all([
        recommendationsApi.getCurrent(params),
        recommendationsApi.getMetadata()
      ])
      
      setRecommendations(recommendationsResponse.data)
      setLastPollTime(new Date())
      
      // Pass metadata to parent
      if (onMetadataUpdate) {
        onMetadataUpdate(metadataResponse.data)
      }
    } catch (err: any) {
      console.error('Error fetching recommendations:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to fetch recommendations')
    } finally {
      setLoading(false)
    }
  }, [onMetadataUpdate]) // Add filterOptions dependency

  // Frontend filtering logic
  const filteredRecommendations = useMemo(() => {
    if (!recommendations.length) return []
    
    return recommendations.filter((rec) => {
      // Symbol filter
      if (filters.symbol && filters.symbol.trim()) {
        if (!rec.symbol.toLowerCase().includes(filters.symbol.trim().toLowerCase())) {
          return false
        }
      }
      
      // Option type filter
      if (filters.option_type && filters.option_type !== '') {
        if (rec.option_type !== filters.option_type) {
          return false
        }
      }
      
      // Score range filter
      if (rec.score < filters.score_range[0] || rec.score > filters.score_range[1]) {
        return false
      }
      
      // ROI range filter (using annualized_roi)
      if (rec.annualized_roi !== null && rec.annualized_roi !== undefined) {
        if (rec.annualized_roi < filters.roi_range[0] || rec.annualized_roi > filters.roi_range[1]) {
          return false
        }
      }
      
      // Max collateral filter
      if (rec.collateral && rec.collateral > filters.max_collateral) {
        return false
      }
      
      return true
    })
  }, [recommendations, filters])

  // Frontend sorting logic
  const sortedRecommendations = useMemo(() => {
    if (!filteredRecommendations.length) return []
    
    return [...filteredRecommendations].sort((a, b) => {
      let aValue: any
      let bValue: any
      
      switch (sortConfig.field) {
        case 'strike':
          aValue = a.strike || 0
          bValue = b.strike || 0
          break
        case 'current_price':
          aValue = a.current_price || 0
          bValue = b.current_price || 0
          break
        case 'total_credit':
          aValue = a.total_credit || 0
          bValue = b.total_credit || 0
          break
        case 'annualized_roi':
          aValue = a.annualized_roi || 0
          bValue = b.annualized_roi || 0
          break
        case 'score':
          aValue = a.score || 0
          bValue = b.score || 0
          break
        case 'symbol':
          aValue = (a.symbol || '').toLowerCase()
          bValue = (b.symbol || '').toLowerCase()
          break
        case 'created_at':
          aValue = new Date(a.created_at || 0).getTime()
          bValue = new Date(b.created_at || 0).getTime()
          break
        default:
          aValue = a.score || 0
          bValue = b.score || 0
      }
      
      if (sortConfig.direction === 'asc') {
        return aValue > bValue ? 1 : aValue < bValue ? -1 : 0
      } else {
        return aValue < bValue ? 1 : aValue > bValue ? -1 : 0
      }
    })
  }, [filteredRecommendations, sortConfig])

  const updateFilterOptions = useCallback(() => {
    if (!recommendations.length) return
    
    // Calculate ranges from actual data
    const scores = recommendations.map(r => r.score).filter(s => s !== null && s !== undefined)
    const rois = recommendations.map(r => r.annualized_roi).filter(r => r !== null && r !== undefined)
    const collaterals = recommendations.map(r => r.collateral).filter(c => c !== null && c !== undefined)
    
    const newOptions = {
      score_range: {
        min: scores.length > 0 ? Math.min(...scores) : 0,
        max: scores.length > 0 ? Math.max(...scores) : 1
      },
      roi_range: {
        min: rois.length > 0 ? Math.min(...rois) : 0,
        max: rois.length > 0 ? Math.max(...rois) : 100
      },
      max_collateral: collaterals.length > 0 ? Math.max(...collaterals) : 100000
    }
    
    setFilterOptions(newOptions)
    
    // Update filter ranges to match actual data ranges (only if filters are at defaults)
    setFilters(prev => ({
      ...prev,
      score_range: [newOptions.score_range.min, newOptions.score_range.max],
      roi_range: [newOptions.roi_range.min, newOptions.roi_range.max],
      max_collateral: newOptions.max_collateral,
    }))
  }, [recommendations])

  const handleGenerateRecommendations = async () => {
    // Always delegate to parent component
    if (onGenerateRecommendations) {
      onGenerateRecommendations()
    }
  }

  const handleRefresh = async () => {
    if (onRefresh) {
      onRefresh()
      return
    }
    
    try {
      setRefreshing(true)
      setError(null)
      await fetchRecommendations()
    } catch (err: any) {
      console.error('Error refreshing recommendations:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to refresh recommendations')
    } finally {
      setRefreshing(false)
    }
  }

  const handleDismiss = async (id: number) => {
    try {
      await recommendationsApi.dismiss(id)
      setRecommendations(prev => prev.filter(rec => rec.id !== id))
    } catch (err: any) {
      console.error('Error dismissing recommendation:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to dismiss recommendation')
    }
  }

  const handleTrade = (recommendation: any) => {
    // TODO: Implement trade functionality
    console.log('Trade clicked for:', recommendation)
  }

  const handleFilterChange = (key: keyof Filters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const handleSortChange = (field: string) => {
    setSortConfig(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'desc' ? 'asc' : 'desc'
    }))
  }

  const clearFilters = useCallback(() => {
    setFilters({
      symbol: '',
      option_type: '',
      score_range: [filterOptions.score_range.min, filterOptions.score_range.max],
      roi_range: [filterOptions.roi_range.min, filterOptions.roi_range.max],
      max_collateral: filterOptions.max_collateral,
    })
  }, [filterOptions])

  // Set up polling effect
  useEffect(() => {
    let intervalId: NodeJS.Timeout
    
    if (pollingEnabled && pollingInterval > 0) {
      intervalId = setInterval(() => {
        fetchRecommendations()
      }, pollingInterval * 60 * 1000)
    }
    
    return () => {
      if (intervalId) {
        clearInterval(intervalId)
      }
    }
  }, [pollingEnabled, pollingInterval, fetchRecommendations])

  // Update filter options when recommendations change
  useEffect(() => {
    updateFilterOptions()
  }, [updateFilterOptions])

  // Clear filters when clearTrigger changes
  useEffect(() => {
    if (clearTrigger > 0) {
      clearFilters()
    }
  }, [clearTrigger, clearFilters])

  // Initial data fetch
  useEffect(() => {
    fetchRecommendations()
    
    // Set up refresh ref for parent component
    if (onRefresh) {
      onRefresh()
    }
  }, [])

  const formatScore = (score: number) => {
    if (score >= 0.8) return 'success'
    if (score >= 0.6) return 'warning'
    return 'error'
  }

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'success'
    if (score >= 0.6) return 'warning'
    return 'error'
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatExpiry = (expiryString: string) => {
    const expiry = new Date(expiryString)
    const now = new Date()
    const daysToExpiry = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
    return `${daysToExpiry}d`
  }

  const getSortIcon = (field: string) => {
    if (sortConfig.field !== field) return null
    return sortConfig.direction === 'asc' ? '↑' : '↓'
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>

      {actualRefreshing && <LinearProgress sx={{ mb: 2 }} />}
      
      {/* Generation Status is now handled by parent component */}
      
      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Filters and Controls */}
      {filtersVisible && (
        <Paper sx={{ mb: 2, p: 2, borderRadius: 0 }} elevation={1}>
          {/* Compact filter layout */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            
            {/* Row 1: Basic Filters + Controls */}
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'flex-end' }}>
              <TextField
                label="Symbol"
                size="small"
                value={filters.symbol}
                onChange={(e) => handleFilterChange('symbol', e.target.value)}
                placeholder="AAPL"
                sx={{ minWidth: 100 }}
              />
              <FormControl size="small" sx={{ minWidth: 100 }}>
                <InputLabel>Type</InputLabel>
                <Select
                  value={filters.option_type}
                  label="Type"
                  onChange={(e) => handleFilterChange('option_type', e.target.value)}
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="put">Put</MenuItem>
                  <MenuItem value="call">Call</MenuItem>
                </Select>
              </FormControl>
              
              {/* Auto-refresh controls inline */}
              <FormControlLabel
                control={
                  <Switch
                    size="small"
                    checked={pollingEnabled}
                    onChange={(e) => setPollingEnabled(e.target.checked)}
                  />
                }
                label="Auto-refresh"
                sx={{ ml: 1 }}
              />
              {pollingEnabled && (
                <FormControl size="small" sx={{ minWidth: 80 }}>
                  <InputLabel>Interval</InputLabel>
                  <Select
                    value={pollingInterval}
                    label="Interval"
                    onChange={(e) => setPollingInterval(e.target.value as number)}
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
            </Box>

            {/* Row 2: Range Filters - Compact horizontal sliders */}
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
              <Box sx={{ minWidth: 180, flex: 1 }}>
                <Typography variant="caption" sx={{ display: 'block', mb: 0.5, fontSize: '0.7rem' }}>
                  Score: {filters.score_range[0].toFixed(2)} - {filters.score_range[1].toFixed(2)}
                </Typography>
                <Slider
                  value={filters.score_range}
                  onChange={(_, value) => {
                    const [min, max] = value as number[]
                    handleFilterChange('score_range', [min, max])
                  }}
                  min={filterOptions.score_range.min}
                  max={filterOptions.score_range.max}
                  step={0.01}
                  size="small"
                  sx={{ height: 4 }}
                />
              </Box>
              
              <Box sx={{ minWidth: 180, flex: 1 }}>
                <Typography variant="caption" sx={{ display: 'block', mb: 0.5, fontSize: '0.7rem' }}>
                  ROI: {filters.roi_range[0].toFixed(1)}% - {filters.roi_range[1].toFixed(1)}%
                </Typography>
                <Slider
                  value={filters.roi_range}
                  onChange={(_, value) => {
                    const [min, max] = value as number[]
                    handleFilterChange('roi_range', [min, max])
                  }}
                  min={filterOptions.roi_range.min}
                  max={filterOptions.roi_range.max}
                  step={0.1}
                  size="small"
                  sx={{ height: 4 }}
                />
              </Box>
              
              <Box sx={{ minWidth: 180, flex: 1 }}>
                <Typography variant="caption" sx={{ display: 'block', mb: 0.5, fontSize: '0.7rem' }}>
                  Max Collateral: ${filters.max_collateral.toLocaleString()}
                </Typography>
                <Slider
                  value={filters.max_collateral}
                  onChange={(_, value) => {
                    handleFilterChange('max_collateral', value as number)
                  }}
                  min={1000}
                  max={filterOptions.max_collateral}
                  step={1000}
                  size="small"
                  sx={{ height: 4 }}
                />
              </Box>
              
              {/* Status info - compact */}
              {lastPollTime && (
                <Typography variant="caption" color="textSecondary" sx={{ fontSize: '0.7rem', ml: 'auto' }}>
                  Updated: {lastPollTime.toLocaleTimeString()}
                </Typography>
              )}
            </Box>
          </Box>
        </Paper>
      )}

      {/* Recommendations Table */}
      {sortedRecommendations.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography color="textSecondary" variant="body2">
            No recommendations available
          </Typography>
        </Box>
      ) : (
        <TableContainer component={Paper} sx={{ borderRadius: 0 }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ 
                backgroundColor: 'background.paper',
                borderBottom: '2px solid',
                borderColor: 'divider'
              }}>
                <TableCell sx={{ 
                  fontWeight: 600, 
                  fontSize: '0.875rem',
                  color: 'text.primary',
                  borderBottom: 'none',
                  py: 1.5,
                  width: 40
                }}></TableCell>
                <TableCell 
                  sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5,
                    cursor: 'pointer',
                    '&:hover': { backgroundColor: 'action.hover' }
                  }}
                  onClick={() => handleSortChange('symbol')}
                >
                  Symbol {getSortIcon('symbol')}
                </TableCell>
                <TableCell sx={{ 
                  fontWeight: 600, 
                  fontSize: '0.875rem',
                  color: 'text.primary',
                  borderBottom: 'none',
                  py: 1.5
                }}>Type</TableCell>
                <TableCell 
                  sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5,
                    cursor: 'pointer',
                    '&:hover': { backgroundColor: 'action.hover' }
                  }}
                  onClick={() => handleSortChange('strike')}
                >
                  Strike {getSortIcon('strike')}
                </TableCell>
                <TableCell sx={{ 
                  fontWeight: 600, 
                  fontSize: '0.875rem',
                  color: 'text.primary',
                  borderBottom: 'none',
                  py: 1.5
                }}>Expiry</TableCell>
                <TableCell 
                  sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5,
                    cursor: 'pointer',
                    '&:hover': { backgroundColor: 'action.hover' }
                  }}
                  onClick={() => handleSortChange('current_price')}
                >
                  Current {getSortIcon('current_price')}
                </TableCell>
                <TableCell 
                  sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5,
                    cursor: 'pointer',
                    '&:hover': { backgroundColor: 'action.hover' }
                  }}
                  onClick={() => handleSortChange('total_credit')}
                >
                  Credit {getSortIcon('total_credit')}
                </TableCell>
                <TableCell 
                  sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5,
                    cursor: 'pointer',
                    '&:hover': { backgroundColor: 'action.hover' }
                  }}
                  onClick={() => handleSortChange('annualized_roi')}
                >
                  ROI {getSortIcon('annualized_roi')}
                </TableCell>
                <TableCell 
                  sx={{ 
                    fontWeight: 600, 
                    fontSize: '0.875rem',
                    color: 'text.primary',
                    borderBottom: 'none',
                    py: 1.5,
                    cursor: 'pointer',
                    '&:hover': { backgroundColor: 'action.hover' }
                  }}
                  onClick={() => handleSortChange('score')}
                >
                  Score {getSortIcon('score')}
                </TableCell>
                <TableCell sx={{ 
                  fontWeight: 600, 
                  fontSize: '0.875rem',
                  color: 'text.primary',
                  borderBottom: 'none',
                  py: 1.5
                }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {sortedRecommendations.map((recommendation) => (
                <React.Fragment key={recommendation.id}>
                  <TableRow 
                    sx={{ 
                      '&:hover': { 
                        backgroundColor: 'action.hover',
                        transition: 'background-color 0.2s ease-in-out'
                      },
                      '& td': { 
                        borderBottom: '1px solid',
                        borderColor: 'divider',
                        py: 1.5
                      }
                    }}
                  >
                    {/* Expand/Collapse */}
                    <TableCell>
                      <IconButton
                        size="small"
                        onClick={() => setExpandedRows(prev => ({
                          ...prev,
                          [recommendation.id]: !prev[recommendation.id]
                        }))}
                        sx={{ p: 0.5 }}
                      >
                        {expandedRows[recommendation.id] ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      </IconButton>
                    </TableCell>

                    {/* Symbol */}
                    <TableCell>
                      <Box>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {recommendation.underlying_ticker || recommendation.symbol}
                        </Typography>
                        <Typography variant="caption" color="textSecondary">
                          {recommendation.name || 'N/A'}
                        </Typography>
                      </Box>
                    </TableCell>

                    {/* Option Type */}
                    <TableCell>
                      <Chip
                        label={recommendation.option_type?.toUpperCase() || 'PUT'}
                        size="small"
                        color="primary"
                        sx={{ borderRadius: 0, height: 20, fontSize: '0.7rem' }}
                      />
                    </TableCell>

                    {/* Strike */}
                    <TableCell>
                      <Typography variant="body2">
                        {recommendation.strike ? `$${recommendation.strike.toFixed(2)}` : 'N/A'}
                      </Typography>
                    </TableCell>

                    {/* Expiry */}
                    <TableCell>
                      <Typography variant="body2">
                        {recommendation.expiry ? formatExpiry(recommendation.expiry) : 'N/A'}
                      </Typography>
                    </TableCell>

                    {/* Current Price */}
                    <TableCell>
                      <Typography variant="body2">
                        {recommendation.current_price ? `$${recommendation.current_price.toFixed(2)}` : 'N/A'}
                      </Typography>
                    </TableCell>

                    {/* Credit */}
                    <TableCell>
                      <Typography variant="body2" sx={{ color: 'success.main', fontWeight: 500 }}>
                        {recommendation.total_credit ? `$${recommendation.total_credit.toFixed(0)}` : 'N/A'}
                      </Typography>
                    </TableCell>

                    {/* ROI */}
                    <TableCell>
                      <Typography variant="body2" sx={{ color: 'success.main', fontWeight: 500 }}>
                        {recommendation.annualized_roi ? `${recommendation.annualized_roi.toFixed(1)}%` : 'N/A'}
                      </Typography>
                    </TableCell>

                    {/* Score */}
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            fontWeight: 600,
                            color: getScoreColor(recommendation.score) === 'success' ? 'success.main' : 
                                   getScoreColor(recommendation.score) === 'warning' ? 'warning.main' : 'error.main'
                          }}
                        >
                          {Math.round(recommendation.score * 100)}
                        </Typography>
                      </Box>
                    </TableCell>

                    {/* Actions */}
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        <Tooltip title="Trade this option">
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleTrade(recommendation)}
                            sx={{ p: 0.5 }}
                          >
                            <TradeIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Dismiss recommendation">
                          <IconButton
                            size="small"
                            onClick={() => handleDismiss(recommendation.id)}
                            sx={{ p: 0.5 }}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>

                  {/* Expanded Card View */}
                  {expandedRows[recommendation.id] && (
                    <TableRow>
                      <TableCell colSpan={10} sx={{ p: 0, border: 0 }}>
                        <Card variant="outlined" sx={{ m: 1, borderRadius: 0 }}>
                          <CardContent sx={{ p: 2 }}>
                            <Grid container spacing={2}>
                              {/* Key Financial Metrics */}
                              <Grid item xs={12} md={6}>
                                <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
                                  Financial Metrics
                                </Typography>
                                <Grid container spacing={1}>
                                  <Grid item xs={6}>
                                    <Typography variant="caption" color="textSecondary">Premium</Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                      {recommendation.contract_price ? `$${recommendation.contract_price.toFixed(2)}` : 'N/A'}
                                    </Typography>
                                  </Grid>
                                  <Grid item xs={6}>
                                    <Typography variant="caption" color="textSecondary">Collateral</Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                      {recommendation.collateral ? `$${recommendation.collateral.toFixed(0)}` : 'N/A'}
                                    </Typography>
                                  </Grid>
                                  <Grid item xs={6}>
                                    <Typography variant="caption" color="textSecondary">Volume</Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                                      {recommendation.volume ? recommendation.volume.toLocaleString() : 'N/A'}
                                    </Typography>
                                  </Grid>
                                  <Grid item xs={6}>
                                    <Typography variant="caption" color="textSecondary">Created</Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                                      {formatDate(recommendation.created_at)}
                                    </Typography>
                                  </Grid>
                                </Grid>
                              </Grid>

                              {/* Company Information */}
                              <Grid item xs={12} md={6}>
                                <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
                                  Company Details
                                </Typography>
                                <Grid container spacing={1}>
                                  <Grid item xs={6}>
                                    <Typography variant="caption" color="textSecondary">Sector</Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                                      {recommendation.sector || 'N/A'}
                                    </Typography>
                                  </Grid>
                                  <Grid item xs={6}>
                                    <Typography variant="caption" color="textSecondary">Industry</Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                                      {recommendation.industry || 'N/A'}
                                    </Typography>
                                  </Grid>
                                  <Grid item xs={6}>
                                    <Typography variant="caption" color="textSecondary">P/E Ratio</Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                                      {recommendation.pe_ratio ? recommendation.pe_ratio.toFixed(1) : 'N/A'}
                                    </Typography>
                                  </Grid>
                                  <Grid item xs={6}>
                                    <Typography variant="caption" color="textSecondary">P/C Ratio</Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                                      {recommendation.put_call_ratio ? recommendation.put_call_ratio.toFixed(2) : 'N/A'}
                                    </Typography>
                                  </Grid>
                                  <Grid item xs={6}>
                                    <Typography variant="caption" color="textSecondary">Earnings</Typography>
                                    <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8rem' }}>
                                      {recommendation.next_earnings_date ? 
                                        new Date(recommendation.next_earnings_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) : 'N/A'}
                                    </Typography>
                                  </Grid>
                                </Grid>
                              </Grid>

                              {/* Score Breakdown */}
                              {recommendation.score_breakdown && (
                                <Grid item xs={12}>
                                  <Typography variant="subtitle2" sx={{ mb: 1, color: 'text.secondary' }}>
                                    Score Breakdown
                                  </Typography>
                                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                                    {Object.entries(recommendation.score_breakdown)
                                      .filter(([key]) => !key.toLowerCase().includes('overall'))
                                      .map(([key, value]) => {
                                        const numericValue = parseFloat(value.toString().replace('%', '').replace('$', '').replace(',', ''));
                                        let color = 'text.primary';
                                        
                                        if (key.toLowerCase().includes('yield') || key.toLowerCase().includes('roi')) {
                                          color = numericValue > 20 ? 'success.main' : numericValue > 10 ? 'warning.main' : 'error.main';
                                        } else if (key.toLowerCase().includes('score') || key.toLowerCase().includes('probability')) {
                                          color = numericValue > 70 ? 'success.main' : numericValue > 50 ? 'warning.main' : 'error.main';
                                        } else if (key.toLowerCase().includes('ratio') || key.toLowerCase().includes('volume')) {
                                          color = numericValue > 1000 ? 'success.main' : numericValue > 500 ? 'warning.main' : 'error.main';
                                        }
                                        
                                        return (
                                          <Box key={key} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                            <Typography variant="caption" color="textSecondary">
                                              {key}:
                                            </Typography>
                                            <Typography 
                                              variant="body2" 
                                              sx={{ 
                                                fontWeight: 500, 
                                                fontSize: '0.8rem',
                                                color: color
                                              }}
                                            >
                                              {value as string}
                                            </Typography>
                                          </Box>
                                        );
                                      })}
                                  </Box>
                                </Grid>
                              )}
                            </Grid>
                          </CardContent>
                        </Card>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  )
}
