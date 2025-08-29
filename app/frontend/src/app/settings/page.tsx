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
  Divider,
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

    const getHelperText = () => {
      let helperText = `Default: ${schema.default}`;
      if (schema.min !== undefined && schema.max !== undefined) {
        helperText += ` (Range: ${schema.min}-${schema.max})`;
      } else if (schema.min !== undefined) {
        helperText += ` (Min: ${schema.min})`;
      } else if (schema.max !== undefined) {
        helperText += ` (Max: ${schema.max})`;
      }
      return helperText;
    };

    return (
      <Box>
        <Typography 
          variant="subtitle2" 
          sx={{ 
            mb: 1, 
            fontWeight: 600,
            color: 'text.primary'
          }}
        >
          {schema.description}
        </Typography>
        <TextField
          fullWidth
          value={value || ''}
          onChange={handleChange}
          type={schema.type === 'int' || schema.type === 'float' ? 'number' : 'text'}
          helperText={getHelperText()}
          size="small"
          sx={{
            '& .MuiOutlinedInput-root': {
              height: 40,
              borderRadius: 0,
              '&:hover fieldset': {
                borderColor: 'primary.main',
              },
            },
            '& .MuiInputLabel-root': {
              display: 'none',
            },
          }}
        />
      </Box>
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
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '50vh',
        flexDirection: 'column',
        gap: 2
      }}>
        <CircularProgress size={40} />
        <Typography variant="body2" color="text.secondary">
          Loading settings...
        </Typography>
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
    <Box sx={{ maxWidth: 800, mx: 'auto' }}>
      {/* Header with Action Buttons */}
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        mb: 4,
        p: 3,
        pb: 0
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <SettingsIcon sx={{ mr: 2, fontSize: 32, color: 'primary.main' }} />
          <Typography variant="h4" component="h1" sx={{ fontWeight: 600 }}>
            Application Settings
          </Typography>
        </Box>
        
        {/* Action Buttons */}
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            onClick={fetchSettings}
            startIcon={<RefreshIcon />}
            disabled={saving}
            sx={{ minWidth: 120, borderRadius: 0 }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            onClick={handleSave}
            startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
            disabled={saving}
            sx={{ minWidth: 160, borderRadius: 0 }}
          >
            {saving ? 'Saving...' : 'Save All Settings'}
          </Button>
        </Box>
      </Box>

      {/* Settings Categories */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, px: 3 }}>
        {Object.entries(groupedSettings).map(([category, settings]) => (
                      <Card key={category} sx={{ 
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 0,
              '&:hover': {
                borderColor: 'primary.main',
                boxShadow: 2,
              },
              transition: 'all 0.2s ease-in-out'
            }}>
            <CardHeader
              title={category}
              titleTypographyProps={{ 
                variant: 'h6', 
                fontWeight: 600,
                color: 'primary.main'
              }}
              sx={{ 
                pb: 1,
                '& .MuiCardHeader-content': {
                  minWidth: 0,
                }
              }}
            />
            <Divider />
            <CardContent sx={{ pt: 2 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {settings.map(({ schema, value }) => (
                  <Box key={schema.key}>
                    {renderInputField(schema.key, schema, value)}
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        ))}
      </Box>

      {/* Notifications */}
      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Snackbar>

      <Snackbar
        open={!!success}
        autoHideDuration={6000}
        onClose={() => setSuccess(null)}
        anchorOrigin={{ vertical: 'top', horizontal: 'right' }}
      >
        <Alert severity="success" onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      </Snackbar>
    </Box>
  );
}
