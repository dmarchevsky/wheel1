'use client';

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Box,
  Button,
  IconButton,
  Chip,
  CircularProgress,
  Paper,
} from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';
import { recommendationsApi } from '@/lib/api';

interface Position {
  symbol: string;
  instrument_type: string;
  contract_symbol?: string;
  recommendation_id?: number;
}

interface RecommendationData {
  id: number;
  symbol: string;
  score: number;
  annualized_roi: number;
  strike: number;
  option_type: string;
  expiry: string;
  created_at: string;
  rationale: any;
}

interface RecommendationDetailsDialogProps {
  open: boolean;
  position: Position | null;
  onClose: () => void;
}

export default function RecommendationDetailsDialog({
  open,
  position,
  onClose,
}: RecommendationDetailsDialogProps) {
  const [data, setData] = useState<RecommendationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && position?.recommendation_id) {
      const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
          const response = await recommendationsApi.getById(String(position.recommendation_id));
          setData(response.data);
        } catch (err) {
          setError('Failed to load recommendation details');
          console.error('Error fetching recommendation:', err);
        } finally {
          setLoading(false);
        }
      };
      
      fetchData();
    } else {
      setData(null);
      setError(null);
    }
  }, [open, position?.recommendation_id]);

  const handleClose = () => {
    setData(null);
    setError(null);
    onClose();
  };

  return (
    <Dialog 
      open={open} 
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 0, backgroundColor: 'background.paper' }
      }}
    >
      <DialogTitle sx={{ pb: 1, backgroundColor: 'background.paper' }}>
        <Box>
          <Typography variant="h6" component="div" sx={{ mb: 1 }}>
            Recommendation Details
          </Typography>
          {position && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Chip
                label={position.symbol}
                variant="outlined"
                size="small"
                sx={{ fontWeight: 'bold', fontFamily: 'monospace', borderRadius: 0 }}
              />
              {position.instrument_type === 'option' && (
                <Chip
                  label={position.contract_symbol || 'Option'}
                  variant="outlined"
                  size="small"
                  sx={{ fontFamily: 'monospace', fontSize: '0.75rem', borderRadius: 0 }}
                />
              )}
            </Box>
          )}
        </Box>
      </DialogTitle>
      
      <DialogContent sx={{ pt: 0, backgroundColor: 'background.default' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4, backgroundColor: 'grey.50' }}>
            <CircularProgress />
          </Box>
        ) : error ? (
          <Typography color="error" variant="body2" sx={{ py: 2 }}>{error}</Typography>
        ) : data ? (
          <Box>
            {/* Key Metrics Section */}
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 2 }}>
                <Paper sx={{ p: 2, backgroundColor: 'primary.50', textAlign: 'center', borderRadius: 0 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 'bold', mb: 1 }}>
                    Score
                  </Typography>
                  <Typography variant="h6" color="primary" sx={{ fontWeight: 'bold', fontFamily: 'monospace' }}>
                    {data.score?.toFixed(1) || 'N/A'}
                  </Typography>
                </Paper>
                <Paper sx={{ p: 2, backgroundColor: 'success.50', textAlign: 'center', borderRadius: 0 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 'bold', mb: 1 }}>
                    Annualized ROI
                  </Typography>
                  <Typography variant="h6" color="success.main" sx={{ fontWeight: 'bold', fontFamily: 'monospace' }}>
                    {data.annualized_roi?.toFixed(1) || 'N/A'}%
                  </Typography>
                </Paper>
                <Paper sx={{ p: 2, backgroundColor: 'warning.50', textAlign: 'center', borderRadius: 0 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 'bold', mb: 1 }}>
                    Strike Price
                  </Typography>
                  <Typography variant="h6" color="warning.main" sx={{ fontWeight: 'bold', fontFamily: 'monospace' }}>
                    ${data.strike?.toFixed(2) || 'N/A'}
                  </Typography>
                </Paper>
              </Box>
            </Box>
            
            {/* Option Details Section */}
            <Box sx={{ mb: 2 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Option Details
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 2 }}>
                <Paper sx={{ p: 2, backgroundColor: 'grey.100', textAlign: 'center', borderRadius: 0 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 'bold', mb: 1 }}>
                    Option Type
                  </Typography>
                  <Chip
                    label={data.option_type?.toUpperCase() || 'N/A'}
                    color={data.option_type === 'put' ? 'error' : data.option_type === 'call' ? 'success' : 'default'}
                    variant="filled"
                    sx={{ fontWeight: 'bold', borderRadius: 0 }}
                  />
                </Paper>
                <Paper sx={{ p: 2, backgroundColor: 'grey.100', textAlign: 'center', borderRadius: 0 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 'bold', mb: 1 }}>
                    Expiry Date
                  </Typography>
                  <Typography variant="body1" sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                    {data.expiry || 'N/A'}
                  </Typography>
                </Paper>
                <Paper sx={{ p: 2, backgroundColor: 'grey.100', textAlign: 'center', borderRadius: 0 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 'bold', mb: 1 }}>
                    Created At
                  </Typography>
                  <Typography variant="body1" sx={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                    {new Date(data.created_at).toLocaleDateString()}
                  </Typography>
                </Paper>
              </Box>
            </Box>
            
            {/* Analysis Details Section */}
            {data.rationale && (
              <Box>
                <Typography variant="h6" sx={{ mb: 2 }}>
                  Analysis Details
                </Typography>
                <Paper sx={{ p: 2, backgroundColor: 'grey.50', borderRadius: 0 }}>
                  {typeof data.rationale === 'string' ? (
                    <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                      {data.rationale}
                    </Typography>
                  ) : (
                    <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
                      {Object.entries(data.rationale).map(([key, value]) => (
                        <Box key={key} sx={{ p: 1.5, backgroundColor: 'grey.200', border: '1px solid', borderColor: 'grey.300', borderRadius: 0 }}>
                          <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                            {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </Typography>
                          <Typography variant="body1" fontWeight="bold" sx={{ fontFamily: 'monospace' }}>
                            {typeof value === 'number' ? value.toFixed(2) : String(value)}
                          </Typography>
                        </Box>
                      ))}
                    </Box>
                  )}
                </Paper>
              </Box>
            )}
          </Box>
        ) : null}
      </DialogContent>
      
      <DialogActions sx={{ p: 2, backgroundColor: 'background.paper' }}>
        <Button 
          onClick={handleClose}
          variant="contained"
          sx={{ borderRadius: 0 }}
        >
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}