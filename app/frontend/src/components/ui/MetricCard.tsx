'use client';

import React from 'react';
import {
  Box,
  Typography,
  Skeleton,
  SxProps,
  Theme,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
} from '@mui/icons-material';
import BaseCard from './BaseCard';

export interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  change?: {
    value: number;
    percent: number;
  };
  loading?: boolean;
  color?: 'primary' | 'success' | 'error' | 'warning' | 'info';
  variant?: 'default' | 'compact';
  sx?: SxProps<Theme>;
}

export default function MetricCard({
  title,
  value,
  subtitle,
  change,
  loading = false,
  color = 'primary',
  variant = 'default',
  sx = {},
}: MetricCardProps) {
  if (loading) {
    return (
      <BaseCard sx={sx}>
        <Box sx={{ p: variant === 'compact' ? 1.5 : 2 }}>
          <Skeleton variant="text" width="60%" height={24} />
          <Skeleton variant="text" width="40%" height={32} />
          {subtitle && <Skeleton variant="text" width="80%" height={20} />}
        </Box>
      </BaseCard>
    );
  }

  const isPositive = change && change.value >= 0;
  const showChange = change !== undefined;

  const formatValue = (val: string | number) => {
    if (typeof val === 'number' && val >= 0) {
      return `$${val.toLocaleString()}`;
    }
    return val;
  };

  return (
    <BaseCard sx={sx}>
      <Box sx={{ p: variant === 'compact' ? 1.5 : 2 }}>
        <Typography 
          color="textSecondary" 
          gutterBottom 
          variant={variant === 'compact' ? 'caption' : 'body2'}
        >
          {title}
        </Typography>
        
        <Typography
          variant={variant === 'compact' ? 'h6' : 'h4'}
          component="div"
          color={showChange ? (isPositive ? 'success.main' : 'error.main') : 'text.primary'}
          sx={{
            display: 'flex',
            alignItems: 'center',
            mb: subtitle ? 1 : 0,
            fontWeight: 600,
          }}
        >
          {showChange && (
            isPositive ? 
              <TrendingUpIcon sx={{ mr: 1, fontSize: variant === 'compact' ? '1rem' : '1.5rem' }} /> : 
              <TrendingDownIcon sx={{ mr: 1, fontSize: variant === 'compact' ? '1rem' : '1.5rem' }} />
          )}
          {formatValue(value)}
        </Typography>
        
        {subtitle && (
          <Typography 
            variant={variant === 'compact' ? 'caption' : 'body2'} 
            color="textSecondary"
          >
            {subtitle}
          </Typography>
        )}
        
        {showChange && (
          <Box sx={{ mt: 1 }}>
            <Typography
              variant={variant === 'compact' ? 'caption' : 'body2'}
              color={isPositive ? 'success.main' : 'error.main'}
              sx={{ 
                display: 'flex', 
                alignItems: 'center',
                fontWeight: 500,
              }}
            >
              {isPositive ? '+' : ''}{change.value >= 0 ? '$' : '-$'}{Math.abs(change.value).toLocaleString()} 
              ({isPositive ? '+' : ''}{change.percent.toFixed(1)}%)
            </Typography>
          </Box>
        )}
      </Box>
    </BaseCard>
  );
}