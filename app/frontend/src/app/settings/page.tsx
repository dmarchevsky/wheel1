'use client';

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Typography,
  TextField,
  Button,
  Grid,
  Alert,
  Snackbar,
  CircularProgress,
} from '@mui/material';
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { settingsApi } from '@/lib/api';

interface SettingSchema {
  key: string;
  type: string;
  default: any;
  min?: number;
  max?: number;
  description: string;
  category: string;
}

interface SettingsData {
  settings: Record<string, any>;
  schema: Record<string, SettingSchema>;
}

export default function SettingsPage() {
  const [settingsData, setSettingsData] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [formData, setFormData] = useState<Record<string, any>>({});

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await settingsApi.getAll();
      setSettingsData(response.data);
      setFormData(response.data.settings);
    } catch (err: any) {
      console.error('Error fetching settings:', err);
      setError('Failed to fetch settings');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (key: string, value: any) => {
    setFormData((prev: Record<string, any>) => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);
      
      // Validate and convert values before saving
      const validatedData: Record<string, any> = {};
      
      for (const [key, value] of Object.entries(formData)) {
        const schema = settingsData?.schema[key];
        if (!schema) continue;
        
        let validatedValue = value;
        
        // Convert to appropriate type and validate
        if (schema.type === 'int') {
          const intValue = parseInt(String(value));
          if (isNaN(intValue)) {
            throw new Error(`Invalid integer value for ${schema.description}`);
          }
          if (schema.min !== undefined && intValue < schema.min) {
            throw new Error(`${schema.description} must be at least ${schema.min}`);
          }
          if (schema.max !== undefined && intValue > schema.max) {
            throw new Error(`${schema.description} must be at most ${schema.max}`);
          }
          validatedValue = intValue;
        } else if (schema.type === 'float') {
          const floatValue = parseFloat(String(value));
          if (isNaN(floatValue)) {
            throw new Error(`Invalid number value for ${schema.description}`);
          }
          if (schema.min !== undefined && floatValue < schema.min) {
            throw new Error(`${schema.description} must be at least ${schema.min}`);
          }
          if (schema.max !== undefined && floatValue > schema.max) {
            throw new Error(`${schema.description} must be at most ${schema.max}`);
          }
          validatedValue = floatValue;
        }
        
        validatedData[key] = validatedValue;
      }
      
      // Update all settings with validated data
      await settingsApi.updateMultiple({ settings: validatedData });
      
      setSuccess('Settings saved successfully');
      
      // Refresh settings to get updated values
      await fetchSettings();
    } catch (err: any) {
      console.error('Error saving settings:', err);
      setError(err.message || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const renderInputField = (key: string, schema: SettingSchema, value: any) => {
    const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = event.target.value;
      handleInputChange(key, newValue);
    };

    return (
      <TextField
        fullWidth
        label={schema.description}
        value={value || ''}
        onChange={handleChange}
        type={schema.type === 'int' || schema.type === 'float' ? 'number' : 'text'}
        helperText={`Default: ${schema.default}${schema.min !== undefined && schema.max !== undefined ? ` (Range: ${schema.min}-${schema.max})` : ''}`}
        size="small"
      />
    );
  };

  const groupSettingsByCategory = () => {
    if (!settingsData) return {};

    const grouped: Record<string, { schema: SettingSchema; value: any }[]> = {};
    
    Object.entries(settingsData.schema).forEach(([key, schema]) => {
      const settingSchema = schema as SettingSchema;
      const category = settingSchema.category;
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push({
        schema: settingSchema,
        value: formData[key] || settingsData.settings[key]
      });
    });

    return grouped;
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error && !settingsData) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        <Button variant="outlined" onClick={fetchSettings} startIcon={<RefreshIcon />}>
          Retry
        </Button>
      </Box>
    );
  }

  const groupedSettings = groupSettingsByCategory();

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <SettingsIcon sx={{ mr: 2, fontSize: 32 }} />
        <Typography variant="h4" component="h1">
          Application Settings
        </Typography>
      </Box>

      <Alert severity="info" sx={{ mb: 3 }}>
        Configure risk parameters and trading settings for the Wheel Strategy application.
        Make your changes and click "Save All Settings" to apply them.
      </Alert>

      <Grid container spacing={3}>
        {Object.entries(groupedSettings).map(([category, settings]) => (
          <Grid item xs={12} key={category}>
            <Card>
              <CardHeader
                title={category}
                titleTypographyProps={{ variant: 'h6', fontWeight: 'bold' }}
              />
              <CardContent>
                <Grid container spacing={2}>
                  {settings.map(({ schema, value }) => (
                    <Grid item xs={12} md={6} key={schema.key}>
                      {renderInputField(schema.key, schema, value)}
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Box sx={{ mt: 3, display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
        <Button
          variant="outlined"
          onClick={fetchSettings}
          startIcon={<RefreshIcon />}
          disabled={saving}
        >
          Refresh
        </Button>
        <Button
          variant="contained"
          onClick={handleSave}
          startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
          disabled={saving}
        >
          {saving ? 'Saving...' : 'Save All Settings'}
        </Button>
      </Box>

      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError(null)}
      >
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Snackbar>

      <Snackbar
        open={!!success}
        autoHideDuration={6000}
        onClose={() => setSuccess(null)}
      >
        <Alert severity="success" onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      </Snackbar>
    </Box>
  );
}
