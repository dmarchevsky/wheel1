'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardHeader,
  CardContent,
  Typography,
  TextField,
  Switch,
  FormControlLabel,
  Button,
  Alert,
  Divider,
  Grid,
  Paper,
  CircularProgress,
  IconButton,
  Collapse,
} from '@mui/material';
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';
import { settingsApi } from '@/lib/api';
import { useThemeContext } from '@/contexts/ThemeContext';

interface Setting {
  key: string;
  value: any;
  type: string;
  description?: string;
}

export default function SettingsTab() {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(true);
  const { isDark, toggleDarkMode, environment } = useThemeContext();

  const fetchSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await settingsApi.getAll();
      // Convert settings object to array format
      const settingsArray = Object.entries(response.data).map(([key, value]) => ({
        key,
        value: typeof value === 'object' ? value.value : value,
        type: typeof value === 'object' ? value.type || typeof value.value : typeof value,
        description: typeof value === 'object' ? value.description : undefined,
      }));
      setSettings(settingsArray);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSettingChange = (key: string, newValue: any) => {
    setSettings(prev => prev.map(setting => 
      setting.key === key ? { ...setting, value: newValue } : setting
    ));
  };

  const handleSaveSettings = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      // Convert settings array back to object format
      const settingsObject = settings.reduce((acc, setting) => ({
        ...acc,
        [setting.key]: setting.value
      }), {});

      await settingsApi.updateMultiple({ settings: settingsObject });
      setSuccess('Settings saved successfully');
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const renderSettingInput = (setting: Setting) => {
    const commonProps = {
      key: setting.key,
      fullWidth: true,
      size: 'small' as const,
      margin: 'normal' as const,
    };

    switch (setting.type) {
      case 'boolean':
        return (
          <FormControlLabel
            control={
              <Switch
                checked={Boolean(setting.value)}
                onChange={(e) => handleSettingChange(setting.key, e.target.checked)}
              />
            }
            label={setting.key.replace(/_/g, ' ').toUpperCase()}
            sx={{ mb: 2 }}
          />
        );
      
      case 'number':
        return (
          <TextField
            {...commonProps}
            label={setting.key.replace(/_/g, ' ').toUpperCase()}
            type="number"
            value={setting.value || ''}
            onChange={(e) => handleSettingChange(setting.key, Number(e.target.value))}
            helperText={setting.description}
          />
        );
      
      default:
        return (
          <TextField
            {...commonProps}
            label={setting.key.replace(/_/g, ' ').toUpperCase()}
            value={setting.value || ''}
            onChange={(e) => handleSettingChange(setting.key, e.target.value)}
            helperText={setting.description}
          />
        );
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* App Settings */}
      <Card sx={{ borderRadius: 0 }}>
        <CardHeader
          title="Application Settings"
          action={
            <IconButton onClick={() => setExpanded(!expanded)}>
              {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          }
        />
        <Collapse in={expanded}>
          <CardContent sx={{ pt: 0 }}>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Theme Settings
                  </Typography>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={isDark}
                        onChange={toggleDarkMode}
                      />
                    }
                    label="Dark Mode"
                  />
                </Paper>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    Trading Environment
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Current Environment: <strong>{environment.toUpperCase()}</strong>
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    Use the environment toggle in the header to switch between Live and Sandbox modes.
                  </Typography>
                </Paper>
              </Grid>
            </Grid>
          </CardContent>
        </Collapse>
      </Card>

      {/* Trading Settings */}
      <Card sx={{ borderRadius: 0 }}>
        <CardHeader
          title="Trading Settings"
          action={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Button
                variant="contained"
                startIcon={saving ? <CircularProgress size={16} /> : <SaveIcon />}
                onClick={handleSaveSettings}
                disabled={saving}
                size="small"
              >
                {saving ? 'Saving...' : 'Save'}
              </Button>
              <IconButton onClick={fetchSettings} disabled={loading}>
                <RefreshIcon />
              </IconButton>
            </Box>
          }
        />
        <CardContent sx={{ pt: 0 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          
          {success && (
            <Alert severity="success" sx={{ mb: 2 }}>
              {success}
            </Alert>
          )}

          <Grid container spacing={3}>
            {settings.map((setting) => (
              <Grid item xs={12} md={6} key={setting.key}>
                {renderSettingInput(setting)}
              </Grid>
            ))}
            
            {settings.length === 0 && (
              <Grid item xs={12}>
                <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 4 }}>
                  No settings found. Initialize settings from the backend to see configuration options.
                </Typography>
              </Grid>
            )}
          </Grid>
        </CardContent>
      </Card>
    </Box>
  );
}