'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardHeader,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Collapse,
  Tooltip,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Refresh as RefreshIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { accountApi } from '@/lib/api';
import RecommendationDetailsDialog from '@/components/RecommendationDetailsDialog';

interface Position {
  symbol: string;
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
      const response = await accountApi.getPositions();
      console.log('Positions data:', response.data);
      // Debug: Check which positions have recommendation_id
      const positionsWithRec = response.data.filter((p: Position) => p.recommendation_id);
      console.log('Positions with recommendation_id:', positionsWithRec);
      setPositions(response.data);
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


  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getPnLColor = (pnl: number) => {
    if (pnl > 0) return 'success.main';
    if (pnl < 0) return 'error.main';
    return 'text.primary';
  };

  const stockPositions = positions.filter((p: Position) => p.instrument_type === 'equity');
  const optionPositions = positions.filter((p: Position) => p.instrument_type === 'option');

  const renderStockTable = () => (
    <TableContainer component={Paper} elevation={0} sx={{ borderRadius: 0 }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Symbol</TableCell>
            <TableCell align="right">Quantity</TableCell>
            <TableCell align="right">Avg Cost</TableCell>
            <TableCell align="right">Cost Basis</TableCell>
            <TableCell align="right">Current Price</TableCell>
            <TableCell align="right">Market Value</TableCell>
            <TableCell align="right">P&L</TableCell>
            <TableCell align="right">P&L %</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {stockPositions.map((position: Position, index: number) => {
            const avgCost = position.cost_basis / position.quantity;
            return (
              <TableRow key={index}>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" fontWeight="medium" sx={{ fontFamily: 'monospace' }}>
                      {position.symbol}
                    </Typography>
                    {position.recommendation_id && (
                      <Tooltip title="View original recommendation">
                        <IconButton 
                          size="small" 
                          onClick={() => handleShowRecommendation(position)}
                          sx={{ p: 0.5 }}
                        >
                          <InfoIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {position.quantity}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {formatCurrency(avgCost)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {formatCurrency(position.cost_basis)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {formatCurrency(position.current_price)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {formatCurrency(position.market_value)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                    {position.pnl > 0 ? <TrendingUpIcon fontSize="small" color="success" /> :
                     position.pnl < 0 ? <TrendingDownIcon fontSize="small" color="error" /> : null}
                    <Typography variant="body2" sx={{ color: getPnLColor(position.pnl) }}>
                      {formatCurrency(position.pnl)}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ color: getPnLColor(position.pnl) }}>
                    {formatPercent(position.pnl_percent)}
                  </Typography>
                </TableCell>
              </TableRow>
            );
          })}
          {stockPositions.length === 0 && (
            <TableRow>
              <TableCell colSpan={8} align="center">
                <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                  No stock positions found
                </Typography>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );

  const renderOptionTable = () => (
    <TableContainer component={Paper} elevation={0} sx={{ borderRadius: 0 }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Symbol</TableCell>
            <TableCell>Contract</TableCell>
            <TableCell>Type</TableCell>
            <TableCell>Side</TableCell>
            <TableCell align="right">Quantity</TableCell>
            <TableCell align="right">Avg Cost</TableCell>
            <TableCell align="right">Cost Basis</TableCell>
            <TableCell align="right">Current Price</TableCell>
            <TableCell align="right">Market Value</TableCell>
            <TableCell align="right">P&L</TableCell>
            <TableCell align="right">P&L %</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {optionPositions.map((position: Position, index: number) => {
            const avgCost = position.cost_basis / (Math.abs(position.quantity) * 100);
            return (
              <TableRow key={index}>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Typography variant="body2" fontWeight="medium" sx={{ fontFamily: 'monospace' }}>
                      {position.symbol}
                    </Typography>
                    {position.recommendation_id && (
                      <Tooltip title="View original recommendation">
                        <IconButton 
                          size="small" 
                          onClick={() => handleShowRecommendation(position)}
                          sx={{ p: 0.5 }}
                        >
                          <InfoIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>
                </TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    {position.contract_symbol}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Chip
                    label={position.option_type?.toUpperCase() || 'N/A'}
                    size="small"
                    color={position.option_type === 'put' ? 'error' : position.option_type === 'call' ? 'success' : 'default'}
                    variant="filled"
                    sx={{ fontWeight: 'medium', fontSize: '0.75rem', minWidth: '50px' }}
                  />
                </TableCell>
                <TableCell>
                  <Chip
                    label={position.side?.toUpperCase()}
                    size="small"
                    color={position.side === 'long' ? 'primary' : 'secondary'}
                    variant="outlined"
                  />
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {Math.abs(position.quantity)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {formatCurrency(avgCost)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {formatCurrency(position.cost_basis)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {formatCurrency(position.current_price)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                    {formatCurrency(position.market_value)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 0.5 }}>
                    {position.pnl > 0 ? <TrendingUpIcon fontSize="small" color="success" /> :
                     position.pnl < 0 ? <TrendingDownIcon fontSize="small" color="error" /> : null}
                    <Typography variant="body2" sx={{ color: getPnLColor(position.pnl) }}>
                      {formatCurrency(position.pnl)}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ color: getPnLColor(position.pnl) }}>
                    {formatPercent(position.pnl_percent)}
                  </Typography>
                </TableCell>
              </TableRow>
            );
          })}
          {optionPositions.length === 0 && (
            <TableRow>
              <TableCell colSpan={11} align="center">
                <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                  No option positions found
                </Typography>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200, backgroundColor: 'grey.50' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Stock Positions Section */}
      <Card sx={{ borderRadius: 0, backgroundColor: 'background.paper' }}>
        <CardHeader
          title={`Stock Positions (${stockPositions.length})`}
          action={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <IconButton onClick={fetchPositions} disabled={loading} size="small">
                <RefreshIcon />
              </IconButton>
              <IconButton onClick={() => setStocksExpanded(!stocksExpanded)} size="small">
                {stocksExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
          }
        />
        <Collapse in={stocksExpanded}>
          <CardContent sx={{ pt: 0, backgroundColor: 'background.default' }}>
            {renderStockTable()}
          </CardContent>
        </Collapse>
      </Card>

      {/* Option Positions Section */}
      <Card sx={{ borderRadius: 0, backgroundColor: 'background.paper' }}>
        <CardHeader
          title={`Option Positions (${optionPositions.length})`}
          action={
            <IconButton onClick={() => setOptionsExpanded(!optionsExpanded)} size="small">
              {optionsExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          }
        />
        <Collapse in={optionsExpanded}>
          <CardContent sx={{ pt: 0, backgroundColor: 'background.default' }}>
            {renderOptionTable()}
          </CardContent>
        </Collapse>
      </Card>

      <RecommendationDetailsDialog 
        open={recommendationDialog.open} 
        position={recommendationDialog.position} 
        onClose={handleCloseRecommendationDialog} 
      />
    </Box>
  );
}