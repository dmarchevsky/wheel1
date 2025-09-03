'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Switch,
  FormControlLabel,
  Chip,
  Alert,
  Snackbar,
  CircularProgress,
  useTheme,
} from '@mui/material';
import {
  Science as SandboxIcon,
  BusinessCenter as LiveModeIcon,
} from '@mui/icons-material';
import { tradingEnvironmentApi } from '@/lib/api';
import { TradingEnvironment, EnvironmentStatus } from '@/types';
import { useThemeContext } from '@/contexts/ThemeContext';

interface EnvironmentToggleProps {
  onEnvironmentChange?: (environment: TradingEnvironment) => void;
  collapsed?: boolean;
}

export default function EnvironmentToggle({ onEnvironmentChange, collapsed }: EnvironmentToggleProps) {
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const theme = useTheme();
  const { environment, setEnvironment } = useThemeContext();

  // Fetch current environment status on mount
  useEffect(() => {
    fetchEnvironmentStatus();
  }, []);

  const fetchEnvironmentStatus = async () => {
    try {
      setInitialLoading(true);
      const response = await tradingEnvironmentApi.getStatus();
      const status: EnvironmentStatus = response.data;
      // Update both local and theme context
      setEnvironment(status.current_environment);
    } catch (err) {
      console.error('Failed to fetch environment status:', err);
      setError('Failed to fetch environment status');
    } finally {
      setInitialLoading(false);
    }
  };

  const handleEnvironmentSwitch = async (checked: boolean) => {
    const newEnvironment: TradingEnvironment = checked ? 'sandbox' : 'production';
    
    if (newEnvironment === environment) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const response = await tradingEnvironmentApi.switchEnvironment(newEnvironment);
      
      if (response.data.status === 'success') {
        // Update theme context immediately
        setEnvironment(newEnvironment);
        
        // Check if there's a warning (credentials not configured)
        if (response.data.warning) {
          setSuccess(`⚠️ ${response.data.message}`);
        } else {
          const modeName = newEnvironment === 'sandbox' ? 'Sandbox Mode' : 'Live Mode';
          setSuccess(`Successfully switched to ${modeName}`);
        }
        
        // Notify parent component
        if (onEnvironmentChange) {
          onEnvironmentChange(newEnvironment);
        }
        
        // Refresh the page after a short delay to update all components
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      } else {
        throw new Error(response.data.message || 'Failed to switch environment');
      }
    } catch (err: any) {
      console.error('Failed to switch environment:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to switch environment');
    } finally {
      setLoading(false);
    }
  };

  const handleCloseSnackbar = () => {
    setError(null);
    setSuccess(null);
  };

  if (initialLoading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <CircularProgress size={16} />
        {!collapsed && (
          <Typography variant="caption" color="text.secondary">
            Loading...
          </Typography>
        )}
      </Box>
    );
  }

  const isSandbox = environment === 'sandbox';

  return (
    <>
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: 1,
        p: collapsed ? 0.5 : 1,
        borderRadius: 1,
        backgroundColor: isSandbox ? 'rgba(255, 152, 0, 0.1)' : 'rgba(76, 175, 80, 0.1)',
        border: `1px solid ${isSandbox ? theme.palette.warning.main : theme.palette.success.main}`,
      }}>
        {!collapsed && (
          <>
            {isSandbox ? <SandboxIcon sx={{ fontSize: 16, color: 'warning.main' }} /> : 
             <LiveModeIcon sx={{ fontSize: 16, color: 'success.main' }} />}
            
            <Typography variant="caption" sx={{ fontWeight: 600, minWidth: 'fit-content' }}>
              {isSandbox ? 'SANDBOX MODE' : 'LIVE MODE'}
            </Typography>
          </>
        )}
        
        {collapsed ? (
          <Chip
            icon={isSandbox ? <SandboxIcon /> : <LiveModeIcon />}
            label=""
            size="small"
            color={isSandbox ? 'warning' : 'success'}
            variant="outlined"
            sx={{ minWidth: 24, '& .MuiChip-label': { display: 'none' } }}
          />
        ) : (
          <FormControlLabel
            control={
              <Switch
                checked={isSandbox}
                onChange={(e) => handleEnvironmentSwitch(e.target.checked)}
                disabled={loading}
                size="small"
                color="warning"
                sx={{
                  '& .MuiSwitch-track': {
                    backgroundColor: isSandbox ? theme.palette.warning.main : theme.palette.success.main,
                  },
                }}
              />
            }
            label={
              <Typography variant="caption" sx={{ fontWeight: 600 }}>
                {loading ? 'Switching...' : 'Sandbox Mode'}
              </Typography>
            }
            sx={{ margin: 0 }}
          />
        )}
        
        {loading && <CircularProgress size={12} />}
      </Box>

      {/* Snackbar for success/error messages */}
      <Snackbar
        open={!!(error || success)}
        autoHideDuration={success?.includes('⚠️') ? 8000 : 6000} // Longer for warnings
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert 
          onClose={handleCloseSnackbar} 
          severity={error ? 'error' : (success?.includes('⚠️') ? 'warning' : 'success')}
          variant="filled"
        >
          {error || success}
        </Alert>
      </Snackbar>
    </>
  );
}
