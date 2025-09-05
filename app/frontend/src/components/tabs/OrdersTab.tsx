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
  Button,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Cancel as CancelIcon,
} from '@mui/icons-material';
import { accountApi } from '@/lib/api';

interface Order {
  order_id: string;
  symbol: string;
  side: string;
  quantity: number;
  order_type: string;
  price?: number;
  status: string;
  duration: string;
  created_at: string;
  filled_quantity?: number;
  avg_fill_price?: number;
}

export default function OrdersTab() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);
  const [cancellingOrders, setCancellingOrders] = useState<Set<string>>(new Set());

  const fetchOrders = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await accountApi.getOrders();
      setOrders(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch orders');
      console.error('Failed to fetch orders:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  const handleCancelOrder = async (orderId: string) => {
    try {
      setCancellingOrders(prev => new Set([...prev, orderId]));
      await accountApi.cancelOrder(orderId);
      // Refresh orders after cancellation
      await fetchOrders();
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to cancel order ${orderId}`);
    } finally {
      setCancellingOrders(prev => {
        const newSet = new Set(prev);
        newSet.delete(orderId);
        return newSet;
      });
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatDateTime = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateString;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'filled':
      case 'executed':
        return 'success';
      case 'cancelled':
      case 'canceled':
        return 'error';
      case 'pending':
      case 'open':
        return 'warning';
      case 'rejected':
        return 'error';
      default:
        return 'default';
    }
  };

  const getSideColor = (side: string) => {
    const lowerSide = side.toLowerCase();
    if (lowerSide.includes('buy')) return 'success';
    if (lowerSide.includes('sell')) return 'error';
    return 'default';
  };

  const canCancelOrder = (status: string) => {
    const lowerStatus = status.toLowerCase();
    return lowerStatus === 'pending' || lowerStatus === 'open' || lowerStatus === 'submitted';
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Card sx={{ borderRadius: 0 }}>
      <CardHeader
        title={`Orders (${orders.length})`}
        action={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <IconButton onClick={fetchOrders} disabled={loading}>
              <RefreshIcon />
            </IconButton>
            <IconButton onClick={() => setExpanded(!expanded)}>
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
        }
      />
      <Collapse in={expanded}>
        <CardContent sx={{ pt: 0 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <TableContainer component={Paper} elevation={0}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Symbol</TableCell>
                  <TableCell>Side</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell align="right">Quantity</TableCell>
                  <TableCell align="right">Price</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Filled</TableCell>
                  <TableCell align="right">Avg Fill Price</TableCell>
                  <TableCell>Duration</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {orders.map((order) => (
                  <TableRow key={order.order_id}>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {order.symbol}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={order.side.toUpperCase()}
                        size="small"
                        color={getSideColor(order.side) as any}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {order.order_type.toUpperCase()}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">{order.quantity}</TableCell>
                    <TableCell align="right">
                      {order.price ? formatCurrency(order.price) : 'Market'}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={order.status.toUpperCase()}
                        size="small"
                        color={getStatusColor(order.status) as any}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="right">
                      {order.filled_quantity || 0} / {order.quantity}
                    </TableCell>
                    <TableCell align="right">
                      {order.avg_fill_price ? formatCurrency(order.avg_fill_price) : '-'}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {order.duration.toUpperCase()}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {formatDateTime(order.created_at)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {canCancelOrder(order.status) && (
                        <IconButton
                          size="small"
                          onClick={() => handleCancelOrder(order.order_id)}
                          disabled={cancellingOrders.has(order.order_id)}
                          color="error"
                        >
                          {cancellingOrders.has(order.order_id) ? (
                            <CircularProgress size={16} />
                          ) : (
                            <CancelIcon />
                          )}
                        </IconButton>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {orders.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={11} align="center">
                      <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                        No orders found
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Collapse>
    </Card>
  );
}