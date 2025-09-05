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
  Grid,
  CircularProgress,
  IconButton,
} from '@mui/material';
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { settingsApi } from '@/lib/api';

interface Setting {
  key: string;
  value: any;
  type: string;
  description?: string;
  category?: string;
  min?: any;
  max?: any;
  default?: any;
}

export default function SettingsTab() {
  const [settings, setSettings] = useState<Setting[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await settingsApi.getAll();
      
      // The response now has both settings values and schema
      const { settings: settingsValues, schema } = response.data;
      
      // Convert to array format with full schema information
      const settingsArray = Object.entries(settingsValues).map(([key, value]) => {
        const schemaInfo = schema[key] || {};
        return {
          key,
          value,
          type: schemaInfo.type || typeof value,
          description: schemaInfo.description,
          category: schemaInfo.category,
          min: schemaInfo.min,
          max: schemaInfo.max,
          default: schemaInfo.default,
        };
      });
      
      // Sort by category and then by key for better organization
      settingsArray.sort((a, b) => {
        if (a.category !== b.category) {
          return (a.category || '').localeCompare(b.category || '');
        }
        return a.key.localeCompare(b.key);
      });
      
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
      fullWidth: true,
      size: 'small' as const,
      margin: 'normal' as const,
    };

    // Create a more user-friendly label
    const label = setting.key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    
    // Create helper text with description and constraints
    let helperText = setting.description || '';
    if (setting.min !== undefined || setting.max !== undefined) {
      const constraints = [];
      if (setting.min !== undefined) constraints.push(`Min: ${setting.min}`);
      if (setting.max !== undefined) constraints.push(`Max: ${setting.max}`);
      if (setting.default !== undefined) constraints.push(`Default: ${setting.default}`);
      if (constraints.length > 0) {
        helperText += helperText ? ` (${constraints.join(', ')})` : `(${constraints.join(', ')})`;
      }
    }

    switch (setting.type) {
      case 'bool':
      case 'boolean':
        return (
          <FormControlLabel
            key={setting.key}
            control={
              <Switch
                checked={Boolean(setting.value)}
                onChange={(e) => handleSettingChange(setting.key, e.target.checked)}
              />
            }
            label={
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {label}
                </Typography>
                {helperText && (
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                    {helperText}
                  </Typography>
                )}
              </Box>
            }
            sx={{ mb: 2, alignItems: 'flex-start' }}
          />
        );
      
      case 'int':
      case 'number':
        return (
          <TextField
            key={setting.key}
            {...commonProps}
            label={label}
            type="number"
            value={setting.value ?? setting.default ?? ''}
            onChange={(e) => handleSettingChange(setting.key, Number(e.target.value))}
            helperText={helperText}
            inputProps={{
              min: setting.min,
              max: setting.max,
            }}
          />
        );
      
      case 'float':
        return (
          <TextField
            key={setting.key}
            {...commonProps}
            label={label}
            type="number"
            inputProps={{
              step: 0.01,
              min: setting.min,
              max: setting.max,
            }}
            value={setting.value ?? setting.default ?? ''}
            onChange={(e) => handleSettingChange(setting.key, parseFloat(e.target.value))}
            helperText={helperText}
          />
        );
      
      default:
        return (
          <TextField
            key={setting.key}
            {...commonProps}
            label={label}
            value={setting.value ?? setting.default ?? ''}
            onChange={(e) => handleSettingChange(setting.key, e.target.value)}
            helperText={helperText}
          />
        );
    }
  };

  // Group settings by category
  const settingsByCategory = settings.reduce((acc, setting) => {
    const category = setting.category || 'General';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(setting);
    return acc;
  }, {} as Record<string, Setting[]>);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Card sx={{ borderRadius: 0 }}>
      <CardHeader
        title="Settings"
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

        {Object.keys(settingsByCategory).length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="body2" color="text.secondary">
              No settings found. Initialize settings from the backend to see configuration options.
            </Typography>
          </Box>
        ) : (
          Object.entries(settingsByCategory).map(([category, categorySettings]) => (
            <Box key={category} sx={{ mb: 4 }}>
              <Typography variant="h6" sx={{ mb: 2, pb: 1, borderBottom: 1, borderColor: 'divider' }}>
                {category}
              </Typography>
              <Grid container spacing={3}>
                {categorySettings.map((setting) => (
                  <Grid item xs={12} md={6} key={setting.key}>
                    {renderSettingInput(setting)}
                  </Grid>
                ))}
              </Grid>
            </Box>
          ))
        )}
      </CardContent>
    </Card>
  );
}