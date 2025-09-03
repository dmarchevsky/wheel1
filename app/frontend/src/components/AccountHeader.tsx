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
  TrendingUp,
  TrendingDown,
} from '@mui/icons-material';
import { accountApi } from '@/lib/api';
import EnvironmentToggle from './EnvironmentToggle';
import { TradingEnvironment } from '@/types';
import { useThemeContext } from '@/contexts/ThemeContext';

interface PortfolioSummary {
  cash: number;
  equity_value: number;
  option_value: number;
  total_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  _error_message?: string; // Optional field for API error information
}

interface AccountHeaderProps {
  collapsed: boolean;
}

export default function AccountHeader({ collapsed }: AccountHeaderProps) {
  const [portfolioData, setPortfolioData] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const { environment: currentEnvironment } = useThemeContext();

  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      setError(null);
      const portfolioRes = await accountApi.getPortfolio();
      setPortfolioData({
        cash: portfolioRes.data.cash,
        equity_value: portfolioRes.data.equity_value,
        option_value: portfolioRes.data.option_value,
        total_value: portfolioRes.data.total_value,
        total_pnl: portfolioRes.data.total_pnl,
        total_pnl_pct: portfolioRes.data.total_pnl_pct,
      });
    } catch (err) {
      console.error('Error fetching portfolio data:', err);
      setError('Failed to fetch portfolio data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolioData();
  }, []);

  const handleRefresh = () => {
    fetchPortfolioData();
  };

  const handleEnvironmentChange = (environment: TradingEnvironment) => {
    // Refresh portfolio data when environment changes
    fetchPortfolioData();
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

  const formatPercent = (value: number | undefined | null) => {
    if (value === undefined || value === null) return '0.00%';
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const getPnLColor = (value: number | undefined | null) => {
    if (value === undefined || value === null || value === 0) return theme.palette.text.secondary;
    return value > 0 ? theme.palette.success.main : theme.palette.error.main;
  };

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
        {error}
      </Alert>
    );
  }

  // Show API error if present in portfolio data
  if (portfolioData?._error_message) {
    return (
      <Alert severity="warning" sx={{ mb: 2 }}>
        {portfolioData._error_message}
      </Alert>
    );
  }

  if (!portfolioData) {
    // Dynamic styling for loading state too
    const loadingCardBackground = currentEnvironment === 'sandbox' 
      ? 'linear-gradient(135deg, #2d1a00 0%, #4a2c00 100%)' 
      : 'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)';
    const loadingCardBorderColor = currentEnvironment === 'sandbox' ? '#ff9800' : '#333';
    
    return (
      <Card sx={{ 
        mb: 3, 
        background: loadingCardBackground, 
        border: `1px solid ${loadingCardBorderColor}`,
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

  // Dynamic styling based on environment
  const isSandbox = currentEnvironment === 'sandbox';
  const cardBackground = isSandbox 
    ? 'linear-gradient(135deg, #2d1a00 0%, #4a2c00 100%)' // Orange/amber gradient for sandbox
    : 'linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%)'; // Default dark gradient
  const cardBorderColor = isSandbox ? '#ff9800' : '#333'; // Orange border for sandbox

  return (
    <Card sx={{ 
      mb: 3, 
      background: cardBackground, 
      border: `1px solid ${cardBorderColor}`,
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
            flexGrow: 1,
            alignItems: 'center'
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Total Value:
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {formatCurrency(portfolioData.total_value)}
              </Typography>
              {portfolioData._error_message && (
                <Typography 
                  variant="caption" 
                  sx={{ 
                    color: 'error.main',
                    fontSize: '0.7rem',
                    fontStyle: 'italic'
                  }}
                >
                  (API Error)
                </Typography>
              )}
              <Box sx={{ display: 'flex', alignItems: 'center', ml: 1 }}>
                {portfolioData.total_pnl >= 0 ? 
                  <TrendingUp sx={{ fontSize: 16, color: getPnLColor(portfolioData.total_pnl) }} /> : 
                  <TrendingDown sx={{ fontSize: 16, color: getPnLColor(portfolioData.total_pnl) }} />
                }
                <Typography 
                  variant="body2" 
                  sx={{ 
                    color: getPnLColor(portfolioData.total_pnl),
                    fontWeight: 600,
                    ml: 0.5
                  }}
                >
                  {formatPercent(portfolioData.total_pnl_pct)}
                </Typography>
              </Box>
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Cash:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600, color: theme.palette.success.main }}>
                {formatCurrency(portfolioData.cash)}
              </Typography>
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Stocks:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600 }}>
                {formatCurrency(portfolioData.equity_value)}
              </Typography>
            </Box>
            
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: { xs: '45%', md: 'auto' } }}>
              <Typography variant="body2" color="text.secondary">
                Options:
              </Typography>
              <Typography variant="body1" sx={{ fontWeight: 600 }}>
                {formatCurrency(portfolioData.option_value)}
              </Typography>
            </Box>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <EnvironmentToggle 
              onEnvironmentChange={handleEnvironmentChange}
              collapsed={collapsed}
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
      </CardContent>
    </Card>
  );
}
