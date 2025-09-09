'use client';

import React from 'react';
import {
  Box,
  Paper,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Typography,
  Divider,
  Collapse,
  SxProps,
  Theme,
} from '@mui/material';

export interface FilterConfig {
  type: 'text' | 'select' | 'range' | 'number';
  key: string;
  label: string;
  options?: { label: string; value: any }[];
  min?: number;
  max?: number;
  step?: number;
  placeholder?: string;
}

export interface FilterPanelProps {
  filters: FilterConfig[];
  values: Record<string, any>;
  onChange: (key: string, value: any) => void;
  onReset?: () => void;
  visible?: boolean;
  sx?: SxProps<Theme>;
}

export default function FilterPanel({
  filters,
  values,
  onChange,
  onReset,
  visible = true,
  sx = {},
}: FilterPanelProps) {
  const renderFilter = (filter: FilterConfig) => {
    const value = values[filter.key];

    switch (filter.type) {
      case 'text':
        return (
          <TextField
            key={filter.key}
            label={filter.label}
            placeholder={filter.placeholder}
            value={value || ''}
            onChange={(e) => onChange(filter.key, e.target.value)}
            size="small"
            fullWidth
          />
        );

      case 'select':
        return (
          <FormControl key={filter.key} size="small" fullWidth>
            <InputLabel>{filter.label}</InputLabel>
            <Select
              value={value || ''}
              label={filter.label}
              onChange={(e) => onChange(filter.key, e.target.value)}
            >
              <MenuItem value="">All</MenuItem>
              {filter.options?.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        );

      case 'number':
        return (
          <TextField
            key={filter.key}
            label={filter.label}
            type="number"
            value={value || ''}
            onChange={(e) => onChange(filter.key, parseFloat(e.target.value) || 0)}
            inputProps={{
              min: filter.min,
              max: filter.max,
              step: filter.step || 1,
            }}
            size="small"
            fullWidth
          />
        );

      case 'range':
        const rangeValue = value || [filter.min || 0, filter.max || 100];
        return (
          <Box key={filter.key} sx={{ px: 1 }}>
            <Typography variant="body2" gutterBottom>
              {filter.label}: {rangeValue[0]} - {rangeValue[1]}
            </Typography>
            <Slider
              value={rangeValue}
              onChange={(_, newValue) => onChange(filter.key, newValue)}
              valueLabelDisplay="auto"
              min={filter.min || 0}
              max={filter.max || 100}
              step={filter.step || 1}
              size="small"
            />
          </Box>
        );

      default:
        return null;
    }
  };

  return (
    <Collapse in={visible}>
      <Paper
        sx={{
          p: 2,
          mb: 2,
          borderRadius: 0,
          backgroundColor: 'background.default',
          ...sx,
        }}
      >
        <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
          Filters
        </Typography>
        <Divider sx={{ mb: 2 }} />
        
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: {
              xs: '1fr',
              sm: 'repeat(2, 1fr)',
              md: 'repeat(3, 1fr)',
              lg: 'repeat(4, 1fr)',
            },
            gap: 2,
          }}
        >
          {filters.map(renderFilter)}
        </Box>
      </Paper>
    </Collapse>
  );
}