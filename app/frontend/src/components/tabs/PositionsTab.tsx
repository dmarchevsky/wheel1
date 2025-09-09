'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Alert,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { accountApi, marketDataApi } from '@/lib/api';
import RecommendationDetailsDialog from '@/components/RecommendationDetailsDialog';
import { 
  DataTable, 
  TableColumn, 
  ExpandableCard, 
  LoadingState, 
  StatusChip, 
  PnLIndicator,
  ActionButton 
} from '@/components/ui';

interface Position {
  symbol: string;
  name?: string;
  instrument_type: string;
  quantity: number;
  cost_basis: number;
  current_price: number;
  market_value: number;
  pnl: number;
  pnl_percent: number;
  contract_symbol?: string;
  option_type?: string;
  recommendation_id?: number;
  strike?: number;
  expiration?: string;
  side?: string;
}


export default function PositionsTab() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [tickerQuotes, setTickerQuotes] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stocksExpanded, setStocksExpanded] = useState(true);
  const [optionsExpanded, setOptionsExpanded] = useState(true);
  const [recommendationDialog, setRecommendationDialog] = useState<{
    open: boolean;
    position: Position | null;
  }>({ open: false, position: null });

  const fetchPositions = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch latest positions data
      const response = await accountApi.getPositions();
      const positionsData = response.data;
      
      // Fetch live ticker quotes for unique symbols
      if (positionsData.length > 0) {
        const uniqueSymbols = [...new Set(positionsData.map((p: Position) => p.symbol))];
        try {
          const quotesResponse = await marketDataApi.getQuote(uniqueSymbols.join(','));
          const quotes = Array.isArray(quotesResponse.data.quote) ? quotesResponse.data.quote : [quotesResponse.data.quote];
          const quotesMap: Record<string, number> = {};
          quotes.forEach((quote: any) => {
            quotesMap[quote.symbol] = quote.last;
          });
          setTickerQuotes(quotesMap);
          
          // Update positions with fresh market data and recalculate P&L if needed
          const updatedPositions = positionsData.map((position: Position) => {
            const livePrice = quotesMap[position.symbol];
            if (livePrice && position.instrument_type === 'equity') {
              // For stocks, we can recalculate market value and P&L with live price
              const marketValue = position.quantity * livePrice;
              const pnl = marketValue - (position.quantity * position.cost_basis);
              const pnlPercent = position.cost_basis !== 0 ? (pnl / (position.quantity * position.cost_basis)) * 100 : 0;
              
              return {
                ...position,
                current_price: livePrice,
                market_value: marketValue,
                pnl,
                pnl_percent: pnlPercent
              };
            }
            return position;
          });
          
          setPositions(updatedPositions);
        } catch (quotesErr) {
          console.warn('Failed to fetch ticker quotes:', quotesErr);
          setPositions(positionsData);
        }
      } else {
        setPositions(positionsData);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch positions');
      console.error('Failed to fetch positions:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPositions();
  }, []);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const handleShowRecommendation = (position: Position) => {
    if (!position.recommendation_id) return;
    
    setRecommendationDialog({
      open: true,
      position
    });
  };

  const handleCloseRecommendationDialog = () => {
    setRecommendationDialog({ open: false, position: null });
  };



  const stockPositions = positions.filter((p: Position) => p.instrument_type === 'equity');
  const optionPositions = positions.filter((p: Position) => p.instrument_type === 'option');

  const stockColumns: TableColumn[] = [
    {
      id: 'symbol',
      label: 'Symbol & Name',
      width: '14%',
      format: (value: string, row: Position) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box>
            <Typography variant="body2" fontWeight="medium">
              {value}
            </Typography>
            {row?.name && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                {row.name}
              </Typography>
            )}
          </Box>
          {row?.recommendation_id && (
            <Tooltip title="View original recommendation">
              <IconButton 
                size="small" 
                onClick={(e) => {
                  e.stopPropagation();
                  handleShowRecommendation(row);
                }}
                sx={{ p: 0.5 }}
              >
                <InfoIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      )
    },
    { 
      id: 'quantity', 
      label: 'Quantity', 
      align: 'right' as const, 
      width: '10%',
      format: (value: number) => value?.toLocaleString() || '0'
    },
    { 
      id: 'cost_basis', 
      label: 'Cost Basis', 
      align: 'right' as const, 
      width: '10%',
      format: (value: number) => formatCurrency(value || 0)
    },
    { 
      id: 'ticker_price', 
      label: 'Ticker Price', 
      align: 'right' as const, 
      width: '10%',
      format: (value: number, row: Position) => formatCurrency(tickerQuotes[row?.symbol] || 0)
    },
    { 
      id: 'current_price', 
      label: 'Position Price', 
      align: 'right' as const, 
      width: '10%',
      format: (value: number, row: Position) => {
        const price = row?.quantity < 0 ? -(value || 0) : (value || 0);
        return formatCurrency(price);
      }
    },
    { 
      id: 'market_value', 
      label: 'Market Value', 
      align: 'right' as const, 
      width: '10%',
      format: (value: number) => formatCurrency(value || 0)
    },
    {
      id: 'pnl',
      label: 'P&L',
      align: 'right' as const,
      width: '10%',
      format: (value: number, row: Position) => (
        <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
          <PnLIndicator 
            value={value} 
            variant="compact"
            showPercentage={false}
          />
        </Box>
      )
    },
    {
      id: 'pnl_percent',
      label: 'P&L %',
      align: 'right' as const,
      width: '10%',
      format: (value: number) => (
        <Typography 
          variant="body2"
          sx={{ 
            color: value >= 0 ? 'success.main' : 'error.main',
            fontWeight: 500
          }}
        >
          {value >= 0 ? '+' : ''}{value?.toFixed(2) || '0.00'}%
        </Typography>
      )
    }
  ];

  const optionColumns: TableColumn[] = [
    {
      id: 'symbol',
      label: 'Symbol & Name',
      width: '14%',
      format: (value: string, row: Position) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box>
            <Typography variant="body2" fontWeight="medium">
              {value}
            </Typography>
            {row?.name && (
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                {row.name}
              </Typography>
            )}
          </Box>
          {row?.recommendation_id && (
            <Tooltip title="View original recommendation">
              <IconButton 
                size="small" 
                onClick={(e) => {
                  e.stopPropagation();
                  handleShowRecommendation(row);
                }}
                sx={{ p: 0.5 }}
              >
                <InfoIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
        </Box>
      )
    },
    {
      id: 'contract_symbol',
      label: 'Contract',
      width: '14%',
      format: (value: string) => (
        <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
          {value && value.length > 25 ? `${value.substring(0, 25)}...` : value || 'N/A'}
        </Typography>
      )
    },
    {
      id: 'option_type',
      label: 'Type',
      width: '10%',
      format: (value: string) => (
        <StatusChip 
          status={value === 'put' ? 'error' : value === 'call' ? 'success' : 'default'}
          label={value?.toUpperCase() || 'N/A'}
        />
      )
    },
    {
      id: 'side',
      label: 'Side',
      width: '8%',
      format: (value: string) => (
        <StatusChip 
          status={value === 'long' ? 'info' : 'warning'}
          label={value?.toUpperCase() || 'N/A'}
        />
      )
    },
    {
      id: 'expiration',
      label: 'Expiration',
      width: '10%',
      format: (value: string) => {
        if (!value) return 'N/A';
        // Format YYYY-MM-DD to MM/DD/YYYY or a shorter format
        try {
          const date = new Date(value);
          return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            year: '2-digit'
          });
        } catch {
          return value;
        }
      }
    },
    { 
      id: 'quantity', 
      label: 'Quantity', 
      align: 'right' as const, 
      width: '10%',
      format: (value: number) => Math.abs(value)
    },
    { 
      id: 'cost_basis', 
      label: 'Cost Basis', 
      align: 'right' as const, 
      width: '10%',
      format: (value: number) => formatCurrency(value || 0)
    },
    { 
      id: 'ticker_price', 
      label: 'Ticker Price', 
      align: 'right' as const, 
      width: '10%',
      format: (value: number, row: Position) => formatCurrency(tickerQuotes[row?.symbol] || 0)
    },
    { 
      id: 'current_price', 
      label: 'Option Price', 
      align: 'right' as const, 
      width: '10%',
      format: (value: number, row: Position) => {
        const price = row?.quantity < 0 ? -(value || 0) : (value || 0);
        return formatCurrency(price);
      }
    },
    { 
      id: 'market_value', 
      label: 'Market Value', 
      align: 'right' as const, 
      width: '10%',
      format: (value: number) => formatCurrency(value || 0)
    },
    {
      id: 'pnl',
      label: 'P&L',
      align: 'right' as const,
      width: '10%',
      format: (value: number, row: Position) => (
        <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
          <PnLIndicator 
            value={value} 
            variant="compact"
            showPercentage={false}
          />
        </Box>
      )
    },
    {
      id: 'pnl_percent',
      label: 'P&L %',
      align: 'right' as const,
      width: '10%',
      format: (value: number) => (
        <Typography 
          variant="body2"
          sx={{ 
            color: value >= 0 ? 'success.main' : 'error.main',
            fontWeight: 500
          }}
        >
          {value >= 0 ? '+' : ''}{value?.toFixed(2) || '0.00'}%
        </Typography>
      )
    }
  ];

  if (loading) {
    return <LoadingState message="Loading positions..." />;
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Stock Positions Section */}
      <ExpandableCard
        title={`Stock Positions (${stockPositions.length})`}
        action={
          <ActionButton 
            onClick={fetchPositions} 
            disabled={loading}
            loading={loading}
            size="small"
            variant="outlined"
            startIcon={<RefreshIcon />}
          >
            Refresh
          </ActionButton>
        }
        defaultExpanded={stocksExpanded}
        onExpandChange={setStocksExpanded}
      >
        <DataTable
          columns={stockColumns}
          data={stockPositions}
          loading={loading}
          emptyMessage="No stock positions found"
          showTotals={true}
          totalsData={{
            quantity: stockPositions.reduce((sum, pos) => sum + (pos.quantity || 0), 0),
            cost_basis: stockPositions.reduce((sum, pos) => sum + (pos.cost_basis || 0), 0),
            market_value: stockPositions.reduce((sum, pos) => sum + (pos.market_value || 0), 0),
            pnl: stockPositions.reduce((sum, pos) => sum + (pos.pnl || 0), 0),
          }}
        />
      </ExpandableCard>

      {/* Option Positions Section */}
      <ExpandableCard
        title={`Option Positions (${optionPositions.length})`}
        action={
          <ActionButton 
            onClick={fetchPositions} 
            disabled={loading}
            loading={loading}
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
          data={optionPositions}
          loading={loading}
          emptyMessage="No option positions found"
          showTotals={true}
          totalsData={{
            quantity: optionPositions.reduce((sum, pos) => sum + Math.abs(pos.quantity || 0), 0),
            cost_basis: optionPositions.reduce((sum, pos) => sum + (pos.cost_basis || 0), 0),
            market_value: optionPositions.reduce((sum, pos) => sum + (pos.market_value || 0), 0),
            pnl: optionPositions.reduce((sum, pos) => sum + (pos.pnl || 0), 0),
          }}
        />
      </ExpandableCard>

      <RecommendationDetailsDialog 
        open={recommendationDialog.open} 
        position={recommendationDialog.position} 
        onClose={handleCloseRecommendationDialog} 
      />
    </Box>
  );
}