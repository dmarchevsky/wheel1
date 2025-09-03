'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  TextField,
  Card,
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
  Switch,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  AlertTitle,
  IconButton,
  Tooltip,
  CircularProgress,
  Container,
  Grid,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Search as SearchIcon,
  Close as CloseIcon,
  ArrowUpward as ArrowUpwardIcon,
  ArrowDownward as ArrowDownwardIcon,
} from '@mui/icons-material';

interface TickerData {
  symbol: string;
  name: string;
  sector: string;
  industry: string;
  market_cap: number;
  beta: number;
  pe_ratio: number;
  dividend_yield: number;
  next_earnings_date: string;
  active: boolean;
  universe_score: number;
  source: string;
  added_at: string;
  updated_at: string;
  current_price: number;
  volume_avg_20d: number;
  volatility_30d: number;
  put_call_ratio: number;
  quote_updated_at: string;
}

export default function TickersPage() {
  const [tickers, setTickers] = useState<TickerData[]>([]);
  const [filteredTickers, setFilteredTickers] = useState<TickerData[]>([]);
  const [loading, setLoading] = useState(true);
  const [addingTicker, setAddingTicker] = useState(false);
  const [newTickerSymbol, setNewTickerSymbol] = useState('');
  const [refreshingTicker, setRefreshingTicker] = useState<string | null>(null);
  const [togglingTicker, setTogglingTicker] = useState<string | null>(null);
  const [removingTicker, setRemovingTicker] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [tickerToDelete, setTickerToDelete] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [filterSymbol, setFilterSymbol] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterSource, setFilterSource] = useState<string>('all');
  const [sortField, setSortField] = useState<string>('symbol');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  const fetchTickers = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Build URL with source filter if specified
      let url = '/api/v1/market-data/interesting-tickers';
      if (filterSource && filterSource !== 'all') {
        url += `?source=${encodeURIComponent(filterSource)}`;
      }
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Failed to fetch tickers');
      }
      const data = await response.json();
      const tickersData = data.data || [];
      setTickers(tickersData);
    } catch (error) {
      console.error('Error fetching tickers:', error);
      setError('Failed to fetch tickers');
    } finally {
      setLoading(false);
    }
  };

  // Apply filters and sorting
  const applyFiltersAndSort = () => {
    let filtered = [...tickers];

    // Apply symbol/name filter
    if (filterSymbol.trim()) {
      filtered = filtered.filter(ticker =>
        ticker.symbol.toLowerCase().includes(filterSymbol.toLowerCase()) ||
        (ticker.name && ticker.name.toLowerCase().includes(filterSymbol.toLowerCase()))
      );
    }

    // Apply status filter
    if (filterStatus !== 'all') {
      filtered = filtered.filter(ticker => {
        if (filterStatus === 'active') return ticker.active;
        if (filterStatus === 'inactive') return !ticker.active;
        return true;
      });
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue: any = a[sortField as keyof TickerData];
      let bValue: any = b[sortField as keyof TickerData];

      // Handle null/undefined values
      if (aValue === null || aValue === undefined) aValue = '';
      if (bValue === null || bValue === undefined) bValue = '';

      // Handle numeric values
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
      }

      // Handle string values
      const aStr = String(aValue).toLowerCase();
      const bStr = String(bValue).toLowerCase();
      
      if (sortDirection === 'asc') {
        return aStr.localeCompare(bStr);
      } else {
        return bStr.localeCompare(aStr);
      }
    });

    setFilteredTickers(filtered);
  };

  // Filter tickers based on symbol
  const handleFilterChange = (value: string) => {
    setFilterSymbol(value);
  };

  // Filter tickers based on status
  const handleStatusFilterChange = (value: string) => {
    setFilterStatus(value);
  };

  // Filter tickers based on source
  const handleSourceFilterChange = (value: string) => {
    setFilterSource(value);
  };

  // Handle sorting
  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  useEffect(() => {
    fetchTickers();
  }, [filterSource]);

  useEffect(() => {
    applyFiltersAndSort();
  }, [tickers, filterSymbol, filterStatus, sortField, sortDirection]);

  const addTicker = async () => {
    if (!newTickerSymbol.trim()) {
      setError('Please enter a ticker symbol');
      return;
    }

    try {
      setAddingTicker(true);
      setError(null);
      const response = await fetch('/api/v1/market-data/interesting-tickers', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ symbol: newTickerSymbol.trim().toUpperCase() }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        const errorMessage = errorData.detail || 'Failed to add ticker';
        
        // Provide user-friendly error messages for common cases
        if (errorMessage.includes('already exists')) {
          setError(`The ticker symbol "${newTickerSymbol.trim().toUpperCase()}" is already in your watchlist.`);
          return;
        }
        
        setError(errorMessage);
        return;
      }

      const data = await response.json();
      setSuccess(data.message);
      setNewTickerSymbol('');
      setFilterSymbol(''); // Clear filter
      setFilterStatus('all'); // Clear status filter
      // Note: Source filter is preserved to maintain user's current view
      fetchTickers(); // Refresh the list
    } catch (error) {
      console.error('Error adding ticker:', error);
      setError(error instanceof Error ? error.message : 'Failed to add ticker');
    } finally {
      setAddingTicker(false);
    }
  };

  const toggleTickerActive = async (symbol: string) => {
    try {
      setTogglingTicker(symbol);
      setError(null);
      const response = await fetch(`/api/v1/market-data/interesting-tickers/${symbol}/toggle`, {
        method: 'PUT',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to toggle ticker');
      }

      const data = await response.json();
      setSuccess(data.message);
      fetchTickers(); // Refresh the list
    } catch (error) {
      console.error('Error toggling ticker:', error);
      setError(error instanceof Error ? error.message : 'Failed to toggle ticker');
    } finally {
      setTogglingTicker(null);
    }
  };

  const refreshTickerData = async (symbol: string) => {
    try {
      setRefreshingTicker(symbol);
      setError(null);
      const response = await fetch(`/api/v1/market-data/interesting-tickers/${symbol}/refresh`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to refresh ticker');
      }

      const data = await response.json();
      setSuccess(data.message);
      fetchTickers(); // Refresh the list
    } catch (error) {
      console.error('Error refreshing ticker:', error);
      setError(error instanceof Error ? error.message : 'Failed to refresh ticker');
    } finally {
      setRefreshingTicker(null);
    }
  };

  const removeTicker = async (symbol: string) => {
    try {
      setRemovingTicker(symbol);
      setError(null);
      const response = await fetch(`/api/v1/market-data/interesting-tickers/${symbol}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to remove ticker');
      }

      const data = await response.json();
      setSuccess(data.message);
      setDeleteDialogOpen(false);
      setTickerToDelete(null);
      fetchTickers(); // Refresh the list
    } catch (error) {
      console.error('Error removing ticker:', error);
      setError(error instanceof Error ? error.message : 'Failed to remove ticker');
    } finally {
      setRemovingTicker(null);
    }
  };

  const handleDeleteClick = (symbol: string) => {
    setTickerToDelete(symbol);
    setDeleteDialogOpen(true);
  };

  const formatMarketCap = (marketCap: number) => {
    if (!marketCap) return 'N/A';
    if (marketCap >= 1000) return `$${(marketCap / 1000).toFixed(1)}T`;
    return `$${marketCap.toFixed(1)}B`;
  };

  const formatPrice = (price: number) => {
    if (!price) return 'N/A';
    return `$${price.toFixed(2)}`;
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString();
  };

  const formatDateTime = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Error and Success Messages */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
          Interesting Tickers Management
        </Typography>
        <Button
          variant="outlined"
          onClick={fetchTickers}
          disabled={loading}
          startIcon={loading ? <CircularProgress size={20} /> : <RefreshIcon />}
          sx={{ borderRadius: 0 }}
        >
          Refresh
        </Button>
      </Box>

      {/* Add New Ticker */}
      <Card sx={{ mb: 3, borderRadius: 0 }}>
        <CardContent>
          <Typography variant="h6" component="h2" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <AddIcon />
            Add New Ticker
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, mb: 1 }}>
            <TextField
              placeholder="Enter ticker symbol (e.g., AAPL)"
              value={newTickerSymbol}
              onChange={(e) => setNewTickerSymbol(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && addTicker()}
              disabled={addingTicker}
              size="small"
              sx={{ 
                flexGrow: 1,
                '& .MuiOutlinedInput-root': {
                  borderRadius: 0,
                },
              }}
            />
            <Button
              variant="contained"
              onClick={addTicker}
              disabled={addingTicker || !newTickerSymbol.trim()}
              startIcon={addingTicker ? <CircularProgress size={20} /> : <AddIcon />}
              sx={{ borderRadius: 0 }}
            >
              Add
            </Button>
          </Box>
          <Typography variant="body2" color="text.secondary">
            Adding a ticker will automatically populate fundamental, industry, and earnings data.
          </Typography>
        </CardContent>
      </Card>

      {/* Tickers Table */}
      <Card sx={{ borderRadius: 0 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" component="h2">
              Tickers ({filteredTickers.length} of {tickers.length})
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <TextField
                placeholder="Filter by symbol or name..."
                value={filterSymbol}
                onChange={(e) => handleFilterChange(e.target.value)}
                size="small"
                sx={{ 
                  width: 250,
                  '& .MuiOutlinedInput-root': {
                    borderRadius: 0,
                  },
                }}
                InputProps={{
                  startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />,
                }}
              />
              {filterSymbol && (
                <IconButton
                  size="small"
                  onClick={() => handleFilterChange('')}
                  sx={{ color: 'text.secondary' }}
                >
                  <CloseIcon />
                </IconButton>
              )}
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Status</InputLabel>
                <Select
                  value={filterStatus}
                  onChange={(e) => handleStatusFilterChange(e.target.value)}
                  label="Status"
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: 0,
                    },
                  }}
                >
                  <MenuItem value="all">All</MenuItem>
                  <MenuItem value="active">Active</MenuItem>
                  <MenuItem value="inactive">Inactive</MenuItem>
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Source</InputLabel>
                <Select
                  value={filterSource}
                  onChange={(e) => handleSourceFilterChange(e.target.value)}
                  label="Source"
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      borderRadius: 0,
                    },
                  }}
                >
                  <MenuItem value="all">All Sources</MenuItem>
                  <MenuItem value="sp500">S&P 500</MenuItem>
                  <MenuItem value="manual">Manual</MenuItem>
                </Select>
              </FormControl>
            </Box>
          </Box>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : filteredTickers.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography color="text.secondary">
                {tickers.length === 0 
                  ? 'No tickers found. Add some tickers to get started.'
                  : 'No tickers match your filter criteria.'
                }
              </Typography>
            </Box>
          ) : (
            <TableContainer component={Paper} variant="outlined" sx={{ '& .MuiPaper-root': { borderRadius: 0 } }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell 
                      sx={{ fontWeight: 'bold', cursor: 'pointer' }}
                      onClick={() => handleSort('symbol')}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        Symbol
                        {sortField === 'symbol' && (
                          sortDirection === 'asc' ? <ArrowUpwardIcon fontSize="small" /> : <ArrowDownwardIcon fontSize="small" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell 
                      sx={{ fontWeight: 'bold', cursor: 'pointer' }}
                      onClick={() => handleSort('name')}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        Name
                        {sortField === 'name' && (
                          sortDirection === 'asc' ? <ArrowUpwardIcon fontSize="small" /> : <ArrowDownwardIcon fontSize="small" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell 
                      sx={{ fontWeight: 'bold', cursor: 'pointer' }}
                      onClick={() => handleSort('sector')}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        Sector
                        {sortField === 'sector' && (
                          sortDirection === 'asc' ? <ArrowUpwardIcon fontSize="small" /> : <ArrowDownwardIcon fontSize="small" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell 
                      sx={{ fontWeight: 'bold', cursor: 'pointer' }}
                      onClick={() => handleSort('market_cap')}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        Market Cap
                        {sortField === 'market_cap' && (
                          sortDirection === 'asc' ? <ArrowUpwardIcon fontSize="small" /> : <ArrowDownwardIcon fontSize="small" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell 
                      sx={{ fontWeight: 'bold', cursor: 'pointer' }}
                      onClick={() => handleSort('current_price')}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        Price
                        {sortField === 'current_price' && (
                          sortDirection === 'asc' ? <ArrowUpwardIcon fontSize="small" /> : <ArrowDownwardIcon fontSize="small" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell 
                      sx={{ fontWeight: 'bold', cursor: 'pointer' }}
                      onClick={() => handleSort('pe_ratio')}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        P/E Ratio
                        {sortField === 'pe_ratio' && (
                          sortDirection === 'asc' ? <ArrowUpwardIcon fontSize="small" /> : <ArrowDownwardIcon fontSize="small" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell 
                      sx={{ fontWeight: 'bold', cursor: 'pointer' }}
                      onClick={() => handleSort('put_call_ratio')}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        Put/Call Ratio
                        {sortField === 'put_call_ratio' && (
                          sortDirection === 'asc' ? <ArrowUpwardIcon fontSize="small" /> : <ArrowDownwardIcon fontSize="small" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell 
                      sx={{ fontWeight: 'bold', cursor: 'pointer' }}
                      onClick={() => handleSort('next_earnings_date')}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        Next Earnings
                        {sortField === 'next_earnings_date' && (
                          sortDirection === 'asc' ? <ArrowUpwardIcon fontSize="small" /> : <ArrowDownwardIcon fontSize="small" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell 
                      sx={{ fontWeight: 'bold', cursor: 'pointer' }}
                      onClick={() => handleSort('source')}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        Source
                        {sortField === 'source' && (
                          sortDirection === 'asc' ? <ArrowUpwardIcon fontSize="small" /> : <ArrowDownwardIcon fontSize="small" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell 
                      sx={{ fontWeight: 'bold', cursor: 'pointer' }}
                      onClick={() => handleSort('active')}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        Status
                        {sortField === 'active' && (
                          sortDirection === 'asc' ? <ArrowUpwardIcon fontSize="small" /> : <ArrowDownwardIcon fontSize="small" />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredTickers.map((ticker) => (
                    <TableRow key={ticker.symbol}>
                      <TableCell sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                        {ticker.symbol}
                      </TableCell>
                      <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {ticker.name || 'N/A'}
                      </TableCell>
                      <TableCell>{ticker.sector || 'N/A'}</TableCell>
                      <TableCell>{formatMarketCap(ticker.market_cap)}</TableCell>
                      <TableCell>{formatPrice(ticker.current_price)}</TableCell>
                      <TableCell>
                        {ticker.pe_ratio ? ticker.pe_ratio.toFixed(2) : 'N/A'}
                      </TableCell>
                      <TableCell>
                        {ticker.put_call_ratio ? ticker.put_call_ratio.toFixed(3) : 'N/A'}
                      </TableCell>
                      <TableCell>{formatDate(ticker.next_earnings_date)}</TableCell>
                      <TableCell>
                        <Chip
                          label={ticker.source}
                          color={ticker.source === 'sp500' ? 'primary' : 'default'}
                          size="small"
                          sx={{ borderRadius: 0 }}
                        />
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Switch
                            checked={ticker.active}
                            onChange={() => toggleTickerActive(ticker.symbol)}
                            disabled={togglingTicker === ticker.symbol}
                          />
                          {togglingTicker === ticker.symbol ? (
                            <CircularProgress size={16} />
                          ) : ticker.active ? (
                            <VisibilityIcon color="success" />
                          ) : (
                            <VisibilityOffIcon color="disabled" />
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                          <Tooltip title="Refresh data">
                            <IconButton
                              size="small"
                              onClick={() => refreshTickerData(ticker.symbol)}
                              disabled={refreshingTicker === ticker.symbol}
                            >
                              {refreshingTicker === ticker.symbol ? (
                                <CircularProgress size={16} />
                              ) : (
                                <RefreshIcon />
                              )}
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Remove ticker">
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => handleDeleteClick(ticker.symbol)}
                              disabled={removingTicker === ticker.symbol}
                            >
                              {removingTicker === ticker.symbol ? (
                                <CircularProgress size={16} />
                              ) : (
                                <DeleteIcon />
                              )}
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Additional Info */}
      <Card sx={{ mt: 3, borderRadius: 0 }}>
        <CardContent>
          <Typography variant="h6" component="h2" sx={{ mb: 2 }}>
            Data Sources
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Chip label="sp500" color="primary" size="small" sx={{ borderRadius: 0 }} />
              <Typography variant="body2">Automatically added from S&P 500 index</Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Chip label="manual" color="default" size="small" sx={{ borderRadius: 0 }} />
              <Typography variant="body2">Manually added by user</Typography>
            </Box>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Fundamental data (sector, earnings, etc.) is updated weekly. Market data (price, volume) is updated frequently.
          </Typography>
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Remove Ticker</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to remove {tickerToDelete}? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} sx={{ borderRadius: 0 }}>Cancel</Button>
          <Button
            color="error"
            onClick={() => tickerToDelete && removeTicker(tickerToDelete)}
            disabled={removingTicker !== null}
            sx={{ borderRadius: 0 }}
          >
            {removingTicker ? <CircularProgress size={20} /> : 'Remove'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
