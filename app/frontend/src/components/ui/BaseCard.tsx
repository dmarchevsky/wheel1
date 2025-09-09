'use client';

import React from 'react';
import { Card, CardProps, SxProps, Theme } from '@mui/material';
import { useThemeContext } from '@/contexts/ThemeContext';

export interface BaseCardProps extends Omit<CardProps, 'sx'> {
  variant?: 'default' | 'outlined' | 'elevated';
  environmentAware?: boolean;
  sx?: SxProps<Theme>;
}

export default function BaseCard({
  variant = 'default',
  environmentAware = true,
  children,
  sx = {},
  ...props
}: BaseCardProps) {
  const { environment } = useThemeContext();
  
  const getCardStyles = (): SxProps<Theme> => {
    const baseStyles: SxProps<Theme> = {
      borderRadius: 0,
    };

    if (environmentAware && environment === 'sandbox') {
      return {
        ...baseStyles,
        background: 'linear-gradient(135deg, #2d1a00 0%, #4a2c00 100%)',
        border: '1px solid #ff9800',
        ...sx,
      };
    }

    switch (variant) {
      case 'outlined':
        return {
          ...baseStyles,
          border: '1px solid',
          borderColor: 'divider',
          ...sx,
        };
      case 'elevated':
        return {
          ...baseStyles,
          elevation: 2,
          ...sx,
        };
      default:
        return {
          ...baseStyles,
          backgroundColor: 'background.paper',
          ...sx,
        };
    }
  };

  return (
    <Card sx={getCardStyles()} {...props}>
      {children}
    </Card>
  );
}