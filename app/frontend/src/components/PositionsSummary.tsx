'use client'

import React, { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Alert,
  Grid,
  useTheme,
  CircularProgress,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
} from '@mui/icons-material'
import { accountApi } from '@/lib/api'
import { Position, OptionPosition } from '@/types'
import { 
  ExpandableCard, 
  DataTable, 
  TableColumn, 
  LoadingState, 
  StatusChip, 
  PnLIndicator,
  ActionButton 
} from '@/components/ui'

interface PortfolioData {
  account_status?: any
  balances?: any
  positions?: Array<{
    symbol: string
    instrument_type: string
    quantity: number
    cost_basis: number
    current_price: number
    market_value: number
    pnl: number
    pnl_percent: number
    contract_symbol?: string
    option_type?: string
    strike?: number
    expiration?: string
    side?: string
  }>
  recent_orders?: any[]
  // Legacy format compatibility
  option_positions?: OptionPosition[]
}

export default function PositionsSummary() {
  const theme = useTheme()
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stockExpanded, setStockExpanded] = useState(true)
  const [optionsExpanded, setOptionsExpanded] = useState(true)

  const fetchPortfolio = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Instead of calling the combined /portfolio endpoint, call individual endpoints
      // This helps us isolate which specific API call is failing
      try {
        console.log('Fetching positions...')
        const positionsResponse = await accountApi.getPositions()
        
        // Create portfolio structure from positions data
        const portfolioData: PortfolioData = {
          positions: positionsResponse.data || []
        }
        
        console.log('Portfolio data constructed:', portfolioData)
        setPortfolio(portfolioData)
        
      } catch (positionsError: any) {
        console.error('Positions API failed, trying fallback approach:', positionsError)
        
        // Fallback: try to get basic balances at least
        try {
          const balancesResponse = await accountApi.getBalances()
          console.log('Got balances as fallback:', balancesResponse.data)
          
          setPortfolio({
            positions: [], // Empty positions if positions API fails
            balances: balancesResponse.data
          })
          
          // Set a warning instead of error for partial success
          setError('Positions data unavailable. Showing account balances only.')
          
        } catch (balancesError: any) {
          throw new Error(`Both positions and balances APIs failed. Positions: ${positionsError.message}, Balances: ${balancesError.message}`)
        }
      }
      
    } catch (err: any) {
      console.error('Error fetching portfolio:', err)
      // Enhanced error handling with specific API error messages
      const errorMsg = err.response?.data?.detail || 
        err.response?.data?.message || 
        err.message || 
        'Failed to fetch portfolio data'
      setError(`API Error: ${errorMsg}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPortfolio()
  }, [])

  if (loading) {
    return <LoadingState message="Loading portfolio data..." />
  }

  if (error) {
    return (
      <Alert 
        severity="error" 
        action={
          <ActionButton 
            onClick={fetchPortfolio} 
            size="small" 
            variant="outlined"
            startIcon={<RefreshIcon />}
          >
            Retry
          </ActionButton>
        }
        sx={{ mb: 2 }}
      >
        {error}
      </Alert>
    )
  }

  if (!portfolio) {
    return (
      <Alert severity="warning">
        No portfolio data available. Please check your Tradier API configuration.
      </Alert>
    )
  }

  // Separate positions by instrument type
  const allPositions = portfolio.positions || []
  const stockPositions = allPositions.filter(pos => pos.instrument_type === 'equity')
  const optionPositions = allPositions.filter(pos => pos.instrument_type === 'option')
  
  // Show only top 5 positions for dashboard summary
  const topStockPositions = stockPositions.slice(0, 5)
  const topOptionPositions = optionPositions.slice(0, 5)

  const stockColumns: TableColumn[] = [
    { id: 'symbol', label: 'Symbol', width: '20%' },
    { id: 'quantity', label: 'Shares', align: 'right', width: '15%', format: (val: number) => Math.abs(val).toLocaleString() },
    { id: 'current_price', label: 'Current Price', align: 'right', width: '20%' },
    { id: 'market_value', label: 'Market Value', align: 'right', width: '20%' },
    {
      id: 'pnl_percent',
      label: 'P&L %',
      align: 'right',
      width: '25%',
      format: (value: number, row: any) => (
        <StatusChip 
          status={row?.pnl && row.pnl > 0 ? 'success' : 'error'}
          label={`${value >= 0 ? '+' : ''}${value?.toFixed(2) || 0}%`}
        />
      )
    }
  ]

  const optionColumns: TableColumn[] = [
    {
      id: 'contract_symbol',
      label: 'Contract',
      width: '35%',
      format: (value: string) => (
        <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
          {value && value.length > 20 ? `${value.substring(0, 20)}...` : value}
        </Typography>
      )
    },
    { id: 'symbol', label: 'Underlying', width: '15%' },
    {
      id: 'side',
      label: 'Side',
      align: 'center',
      width: '15%',
      format: (value: string, row: any) => (
        <StatusChip 
          status={value === 'long' || (row?.quantity && row.quantity > 0) ? 'info' : 'warning'}
          label={value || (row?.quantity && row.quantity > 0 ? 'long' : 'short')}
        />
      )
    },
    { 
      id: 'quantity', 
      label: 'Qty', 
      align: 'right', 
      width: '10%',
      format: (val: number) => Math.abs(val)
    },
    {
      id: 'pnl_percent',
      label: 'P&L %',
      align: 'right',
      width: '25%',
      format: (value: number, row: any) => (
        <StatusChip 
          status={row?.pnl && row.pnl > 0 ? 'success' : 'error'}
          label={`${value >= 0 ? '+' : ''}${value?.toFixed(2) || 0}%`}
        />
      )
    }
  ]

  return (
    <Grid container spacing={3}>
      {/* Stock Positions Summary */}
      <Grid item xs={12} lg={6}>
        <ExpandableCard
          title={`Stock Positions (${stockPositions.length})`}
          action={
            <ActionButton 
              onClick={fetchPortfolio} 
              size="small"
              variant="outlined"
              startIcon={<RefreshIcon />}
            >
              Refresh
            </ActionButton>
          }
          defaultExpanded={stockExpanded}
          onExpandChange={setStockExpanded}
        >
          <DataTable
            columns={stockColumns}
            data={topStockPositions}
            emptyMessage="No stock positions found"
            dense
            maxHeight={300}
          />
          {stockPositions.length > 5 && (
            <Box textAlign="center" mt={2}>
              <Typography variant="body2" color="textSecondary">
                Showing top 5 positions. <a href="/portfolio" style={{ color: theme.palette.primary.main }}>View all positions</a>
              </Typography>
            </Box>
          )}
        </ExpandableCard>
      </Grid>

      {/* Options Positions Summary */}
      <Grid item xs={12} lg={6}>
        <ExpandableCard
          title={`Options Positions (${optionPositions.length})`}
          action={
            <ActionButton 
              onClick={fetchPortfolio} 
              size="small"
              variant="outlined"
              startIcon={<RefreshIcon />}
            >
              Refresh
            </ActionButton>
          }
          defaultExpanded={optionsExpanded}
          onExpandChange={setOptionsExpanded}
        >
          <DataTable
            columns={optionColumns}
            data={topOptionPositions}
            emptyMessage="No options positions found"
            dense
            maxHeight={300}
          />
          {optionPositions.length > 5 && (
            <Box textAlign="center" mt={2}>
              <Typography variant="body2" color="textSecondary">
                Showing top 5 positions. <a href="/portfolio" style={{ color: theme.palette.primary.main }}>View all positions</a>
              </Typography>
            </Box>
          )}
        </ExpandableCard>
      </Grid>
    </Grid>
  )
}
