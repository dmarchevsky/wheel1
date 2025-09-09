'use client';

import React from 'react';
import { Box, CircularProgress, Typography, SxProps, Theme } from '@mui/material';

export interface LoadingStateProps {
  message?: string;
  size?: number;
  variant?: 'centered' | 'inline';
  sx?: SxProps<Theme>;
}

export default function LoadingState({
  message = 'Loading...',
  size = 40,
  variant = 'centered',
  sx = {},
}: LoadingStateProps) {
  const baseStyles: SxProps<Theme> = {
    display: 'flex',
    alignItems: 'center',
    gap: 2,
    ...(variant === 'centered' && {
      justifyContent: 'center',
      minHeight: 200,
      flexDirection: 'column',
    }),
    ...sx,
  };

  return (
    <Box sx={baseStyles}>
      <CircularProgress size={size} />
      {message && (
        <Typography variant="body2" color="textSecondary">
          {message}
        </Typography>
      )}
    </Box>
  );
}