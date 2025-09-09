'use client';

import React from 'react';
import {
  Button,
  ButtonProps,
  CircularProgress,
  SxProps,
  Theme,
} from '@mui/material';

export interface ActionButtonProps extends Omit<ButtonProps, 'sx'> {
  loading?: boolean;
  loadingText?: string;
  variant?: 'contained' | 'outlined' | 'text';
  size?: 'small' | 'medium' | 'large';
  sx?: SxProps<Theme>;
}

export default function ActionButton({
  loading = false,
  loadingText,
  children,
  disabled,
  startIcon,
  variant = 'contained',
  size = 'medium',
  sx = {},
  ...props
}: ActionButtonProps) {
  const isDisabled = disabled || loading;

  const getLoadingIcon = () => {
    if (!loading) return startIcon;
    
    const spinnerSize = size === 'small' ? 16 : size === 'large' ? 24 : 20;
    return <CircularProgress size={spinnerSize} color="inherit" />;
  };

  const buttonText = loading && loadingText ? loadingText : children;

  return (
    <Button
      {...props}
      variant={variant}
      size={size}
      disabled={isDisabled}
      startIcon={getLoadingIcon()}
      sx={{
        borderRadius: 0,
        textTransform: 'none',
        fontWeight: 500,
        minWidth: size === 'small' ? 80 : 100,
        ...sx,
      }}
    >
      {buttonText}
    </Button>
  );
}