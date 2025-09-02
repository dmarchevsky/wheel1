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
  useTheme,
  useMediaQuery,
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
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isTablet = useMediaQuery(theme.breakpoints.down('md'));
  
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
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Typography 
          variant="body2" 
          sx={{ 
            mb: 0.5, 
            fontWeight: 600,
            color: 'text.primary',
            fontSize: '0.875rem',
            lineHeight: 1.3
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
              height: 36,
              borderRadius: 1,
              fontSize: '0.875rem',
              '&:hover fieldset': {
                borderColor: 'primary.main',
              },
            },
            '& .MuiInputLabel-root': {
              display: 'none',
            },
            '& .MuiFormHelperText-root': {
              fontSize: '0.75rem',
              margin: '4px 0 0 0',
              lineHeight: 1.2
            }
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
    <Box sx={{ 
      maxWidth: isMobile ? '100%' : isTablet ? 1000 : 1400, 
      mx: 'auto',
      px: isMobile ? 1 : 0
    }}>
      {/* Compact Header with Action Buttons */}
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        mb: isMobile ? 1 : 2,
        p: isMobile ? 1 : 2,
        pb: isMobile ? 0.5 : 1,
        position: 'sticky',
        top: 0,
        bgcolor: 'background.default',
        zIndex: 10,
        borderBottom: 1,
        borderColor: 'divider',
        flexDirection: isMobile ? 'column' : 'row',
        gap: isMobile ? 1 : 0
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <SettingsIcon sx={{ mr: 1.5, fontSize: isMobile ? 20 : 24, color: 'primary.main' }} />
          <Typography variant={isMobile ? "h6" : "h5"} component="h1" sx={{ fontWeight: 600 }}>
            Settings
          </Typography>
        </Box>
        
        {/* Action Buttons */}
        <Box sx={{ display: 'flex', gap: 1.5, width: isMobile ? '100%' : 'auto' }}>
          <Button
            variant="outlined"
            onClick={fetchSettings}
            startIcon={!isMobile ? <RefreshIcon /> : undefined}
            disabled={saving}
            size="small"
            sx={{ 
              minWidth: isMobile ? 'auto' : 100, 
              borderRadius: 1,
              flex: isMobile ? 1 : 'none'
            }}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            onClick={handleSave}
            startIcon={saving ? <CircularProgress size={16} /> : (!isMobile ? <SaveIcon /> : undefined)}
            disabled={saving}
            size="small"
            sx={{ 
              minWidth: isMobile ? 'auto' : 120, 
              borderRadius: 1,
              flex: isMobile ? 2 : 'none'
            }}
          >
            {saving ? 'Saving...' : isMobile ? 'Save' : 'Save Changes'}
          </Button>
        </Box>
      </Box>

      {/* Settings Categories */}
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        gap: isMobile ? 1.5 : 2, 
        px: isMobile ? 1 : 2 
      }}>
        {Object.entries(groupedSettings).map(([category, settings]) => {
          // Dynamic grid sizing based on number of settings and screen size
          const getGridSize = (settingsCount: number) => {
            if (isMobile) return 12;
            if (isTablet) {
              return settingsCount === 1 ? 12 : 6;
            }
            // Desktop: optimize for screen space
            if (settingsCount === 1) return 12;
            if (settingsCount === 2) return 6;
            if (settingsCount <= 3) return 4;
            return 3; // 4 columns for 4+ settings
          };

          return (
            <Card key={category} sx={{ 
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 1,
              '&:hover': {
                borderColor: 'primary.main',
                boxShadow: 1,
              },
              transition: 'all 0.2s ease-in-out'
            }}>
              <CardHeader
                title={category}
                titleTypographyProps={{ 
                  variant: isMobile ? 'body1' : 'subtitle1', 
                  fontWeight: 600,
                  color: 'primary.main'
                }}
                sx={{ 
                  py: isMobile ? 1 : 1.5,
                  px: isMobile ? 1.5 : 2,
                  '& .MuiCardHeader-content': {
                    minWidth: 0,
                  }
                }}
              />
              <Divider />
              <CardContent sx={{ p: isMobile ? 1.5 : 2 }}>
                <Grid container spacing={isMobile ? 1.5 : 2}>
                  {settings.map(({ schema, value }) => (
                    <Grid 
                      item 
                      xs={12} 
                      sm={6} 
                      md={getGridSize(settings.length)}
                      key={schema.key}
                    >
                      {renderInputField(schema.key, schema, value)}
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>
          );
        })}
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
