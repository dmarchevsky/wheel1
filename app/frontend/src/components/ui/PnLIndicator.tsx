'use client';

import React from 'react';
import { Box, Typography, SxProps, Theme } from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
} from '@mui/icons-material';

export interface PnLIndicatorProps {
  value: number;
  percentage?: number;
  showIcon?: boolean;
  showPercentage?: boolean;
  variant?: 'default' | 'compact';
  sx?: SxProps<Theme>;
}

export default function PnLIndicator({
  value,
  percentage,
  showIcon = true,
  showPercentage = true,
  variant = 'default',
  sx = {},
}: PnLIndicatorProps) {
  const isPositive = value >= 0;
  const isZero = value === 0;
  
  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(Math.abs(val));
  };

  const formatPercent = (val: number) => {
    return `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
  };

  const getColor = () => {
    if (isZero) return 'text.primary';
    return isPositive ? 'success.main' : 'error.main';
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: variant === 'compact' ? 0.5 : 1,
        ...sx,
      }}
    >
      {showIcon && !isZero && (
        isPositive ? 
          <TrendingUpIcon 
            fontSize={variant === 'compact' ? 'small' : 'medium'} 
            color="success" 
          /> :
          <TrendingDownIcon 
            fontSize={variant === 'compact' ? 'small' : 'medium'} 
            color="error" 
          />
      )}
      
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
        <Typography
          variant={variant === 'compact' ? 'body2' : 'body1'}
          sx={{
            color: getColor(),
            fontWeight: 500,
          }}
        >
          {isPositive ? '+' : ''}{formatCurrency(value)}
        </Typography>
        
        {showPercentage && percentage !== undefined && (
          <Typography
            variant={variant === 'compact' ? 'caption' : 'body2'}
            sx={{
              color: getColor(),
              fontWeight: 500,
            }}
          >
            ({formatPercent(percentage)})
          </Typography>
        )}
      </Box>
    </Box>
  );
}