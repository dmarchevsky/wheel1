'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  IconButton,
  Alert,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { BaseCard, LoadingState } from '@/components/ui';
import { accountApi } from '@/lib/api';
import EnvironmentToggle from './EnvironmentToggle';
import { TradingEnvironment } from '@/types';
import { useThemeContext } from '@/contexts/ThemeContext';

interface AccountBalanceData {
  account_number: string;
  total_value: number;
  cash: number;
  long_stock_value: number;
  short_stock_value: number;
  long_option_value: number;
  short_option_value: number;
  buying_power: number;
  day_trade_buying_power: number;
  equity: number;
  margin_info: {
    fed_call: number;
    maintenance_call: number;
    option_buying_power: number;
    stock_buying_power: number;
    stock_short_value: number;
    sweep: number;
  };
  last_updated: string;
}

export default function AccountHeader() {
  const [balanceData, setBalanceData] = useState<AccountBalanceData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { environment: currentEnvironment } = useThemeContext();

  const fetchBalanceData = async () => {
    try {
      setLoading(true);
      setError(null);
      const balancesRes = await accountApi.getBalances();
      setBalanceData(balancesRes.data);
    } catch (err) {
      console.error('Error fetching balance data:', err);
      setError('Failed to fetch balance data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBalanceData();
  }, []);

  const handleRefresh = () => {
    fetchBalanceData();
  };

  const handleEnvironmentChange = (environment: TradingEnvironment) => {
    // Refresh balance data when environment changes
    fetchBalanceData();
  };

  const formatCurrency = (value: number | undefined | null) => {
    if (value === undefined || value === null) return '$0.00';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const getValueColor = (value: number | undefined | null) => {
    if (value === undefined || value === null || value === 0) return theme.palette.text.primary;
    return value > 0 ? theme.palette.success.main : theme.palette.error.main;
  };

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
        {error}
      </Alert>
    );
  }

  if (!balanceData) {
    return (
      <BaseCard 
        environmentAware 
        sx={{ 
          mb: 3, 
          width: '100%',
          ml: 0,
          mr: 0,
        }}
      >
        <LoadingState variant="centered" message="Loading account data..." />
      </BaseCard>
    );
  }

  return (
    <BaseCard 
      environmentAware
      sx={{ 
        mb: 3, 
        width: '100%',
        ml: 0,
        mr: 0,
        py: 3, 
        px: 4 
      }}
    >
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box sx={{ 
            display: 'flex', 
            flexWrap: 'wrap', 
            gap: { xs: 1.5, md: 3 },
            justifyContent: isMobile ? 'space-between' : 'flex-start',
            flexGrow: 1,
            alignItems: 'center'
          }}>
            {/* Account Number & Total Value */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Account {balanceData.account_number}:
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {formatCurrency(balanceData.total_value)}
              </Typography>
            </Box>
            
            {/* Cash */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Cash:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600, color: theme.palette.success.main }}>
                {formatCurrency(balanceData.cash)}
              </Typography>
            </Box>
            
            {/* Long Stock Value */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Long Stock:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600, color: getValueColor(balanceData.long_stock_value) }}>
                {formatCurrency(balanceData.long_stock_value)}
              </Typography>
            </Box>
            
            {/* Short Stock Value */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Short Stock:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600, color: getValueColor(balanceData.short_stock_value) }}>
                {formatCurrency(balanceData.short_stock_value)}
              </Typography>
            </Box>
            
            {/* Long Options Value */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Long Options:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600, color: getValueColor(balanceData.long_option_value) }}>
                {formatCurrency(balanceData.long_option_value)}
              </Typography>
            </Box>
            
            {/* Short Options Value */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Short Options:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600, color: getValueColor(balanceData.short_option_value) }}>
                {formatCurrency(balanceData.short_option_value)}
              </Typography>
            </Box>
            
            {/* Buying Power */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Buying Power:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600, color: theme.palette.info.main }}>
                {formatCurrency(balanceData.buying_power)}
              </Typography>
            </Box>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <EnvironmentToggle 
              onEnvironmentChange={handleEnvironmentChange}
            />
            
            <IconButton 
              onClick={handleRefresh} 
              disabled={loading}
              size="small"
              sx={{ 
                backgroundColor: 'rgba(255,255,255,0.1)', 
                '&:hover': { backgroundColor: 'rgba(255,255,255,0.2)' }
              }}
            >
              {loading ? <CircularProgress size={20} color="inherit" /> : <RefreshIcon />}
            </IconButton>
          </Box>
        </Box>
    </BaseCard>
  );
}
