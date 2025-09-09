'use client';

import React from 'react';
import { Chip, ChipProps } from '@mui/material';

export interface StatusChipProps extends Omit<ChipProps, 'color'> {
  status: 'success' | 'error' | 'warning' | 'info' | 'default' | 'pending' | 'completed' | 'failed';
  value?: string | number;
}

export default function StatusChip({
  status,
  value,
  label,
  ...props
}: StatusChipProps) {
  const getChipProps = () => {
    switch (status) {
      case 'success':
      case 'completed':
        return {
          color: 'success' as const,
          variant: 'filled' as const,
        };
      case 'error':
      case 'failed':
        return {
          color: 'error' as const,
          variant: 'filled' as const,
        };
      case 'warning':
      case 'pending':
        return {
          color: 'warning' as const,
          variant: 'filled' as const,
        };
      case 'info':
        return {
          color: 'info' as const,
          variant: 'filled' as const,
        };
      default:
        return {
          color: 'default' as const,
          variant: 'outlined' as const,
        };
    }
  };

  const displayLabel = label || value?.toString() || status;

  return (
    <Chip
      {...getChipProps()}
      label={displayLabel}
      size="small"
      sx={{
        borderRadius: 0,
        fontWeight: 500,
        fontSize: '0.75rem',
        textTransform: 'uppercase',
        ...props.sx,
      }}
      {...props}
    />
  );
}