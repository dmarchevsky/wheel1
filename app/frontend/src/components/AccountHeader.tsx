'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  IconButton,
  CircularProgress,
  Alert,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { accountApi } from '@/lib/api';
import { AccountBalance } from '@/types';

interface AccountHeaderProps {
  collapsed: boolean;
}

export default function AccountHeader({ collapsed }: AccountHeaderProps) {
  const [accountData, setAccountData] = useState<AccountBalance | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const fetchAccountData = async () => {
    try {
      setLoading(true);
      setError(null);
      const accountRes = await accountApi.getAccountInfo();
      setAccountData(accountRes.data);
    } catch (err) {
      console.error('Error fetching account data:', err);
      setError('Failed to fetch account data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccountData();
  }, []);

  const handleRefresh = () => {
    fetchAccountData();
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
        {error}
      </Alert>
    );
  }

  if (!accountData) {
    return (
      <Card sx={{ 
        mb: 3, 
        background: 'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)', 
        border: '1px solid #333',
        borderRadius: 0,
        width: '100%',
        ml: 0,
        mr: 0,
      }}>
        <CardContent sx={{ py: 3, px: 4 }}>
          <Box sx={{ display: 'flex', justifyContent: 'center' }}>
            <CircularProgress size={24} />
          </Box>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card sx={{ 
      mb: 3, 
      background: 'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)', 
      border: '1px solid #333',
      borderRadius: 0,
      width: '100%',
      ml: 0,
      mr: 0,
    }}>
      <CardContent sx={{ py: 3, px: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ 
            display: 'flex', 
            flexWrap: 'wrap', 
            gap: { xs: 2, md: 4 },
            justifyContent: isMobile ? 'space-between' : 'flex-start',
            flexGrow: 1
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Total:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600 }}>
                {formatCurrency(accountData.total_value)}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Cash:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600 }}>
                {formatCurrency(accountData.cash)}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Equity:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600 }}>
                {formatCurrency(accountData.equity)}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Buying Power:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600 }}>
                {formatCurrency(accountData.buying_power)}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Day Trade:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600 }}>
                {formatCurrency(accountData.day_trade_buying_power)}
              </Typography>
            </Box>
          </Box>
          
          <IconButton 
            onClick={handleRefresh} 
            disabled={loading}
            size="small"
            sx={{ 
              backgroundColor: 'rgba(255,255,255,0.1)', 
              '&:hover': { backgroundColor: 'rgba(255,255,255,0.2)' },
              ml: 2
            }}
          >
            {loading ? <CircularProgress size={20} color="inherit" /> : <RefreshIcon />}
          </IconButton>
        </Box>
      </CardContent>
    </Card>
  );
}
