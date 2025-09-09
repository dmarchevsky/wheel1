'use client';

import React, { useState, useEffect } from 'react';
import { Dialog, Typography, Box, Button, Chip, Divider, CircularProgress } from '@mui/material';
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
          setError('Failed to load details');
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

  const DataRow = ({ label, value }: { label: string; value: any }) => (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', py: 0.25 }}>
      <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>{label}:</Typography>
      <Typography variant="body2" sx={{ fontFamily: 'monospace', fontWeight: 500, fontSize: '0.8rem' }}>
        {value}
      </Typography>
    </Box>
  );

  const formatLabel = (key: string) => {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <Dialog 
      open={open} 
      onClose={onClose} 
      maxWidth="sm" 
      PaperProps={{ sx: { borderRadius: 1, minWidth: 400 } }}
    >
      <Box sx={{ p: 2 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h6" fontWeight={600}>
              Recommendation Details
            </Typography>
            {position && (
              <Chip 
                label={position.symbol} 
                size="small" 
                color="primary" 
                variant="outlined"
                sx={{ fontWeight: 600, fontFamily: 'monospace' }}
              />
            )}
            {position?.contract_symbol && (
              <Chip 
                label={position.contract_symbol} 
                size="small" 
                variant="outlined"
                sx={{ fontSize: '0.7rem' }}
              />
            )}
          </Box>
          <Button onClick={onClose} size="small" variant="outlined" sx={{ minWidth: 'auto', px: 1 }}>
            Close
          </Button>
        </Box>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress size={24} />
          </Box>
        ) : error ? (
          <Typography color="error" variant="body2" sx={{ py: 2 }}>{error}</Typography>
        ) : data ? (
          <Box>
            {/* Key Metrics */}
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 2, mb: 2 }}>
              <Box sx={{ textAlign: 'center', border: '1px solid', borderColor: 'divider', p: 1, borderRadius: 1 }}>
                <Typography variant="caption" color="text.secondary" display="block">Score</Typography>
                <Typography variant="h6" color="primary.main" sx={{ fontFamily: 'monospace', fontWeight: 600 }}>
                  {data.score?.toFixed(1) || 'N/A'}
                </Typography>
              </Box>
              <Box sx={{ textAlign: 'center', border: '1px solid', borderColor: 'divider', p: 1, borderRadius: 1 }}>
                <Typography variant="caption" color="text.secondary" display="block">Annualized ROI</Typography>
                <Typography variant="h6" color="success.main" sx={{ fontFamily: 'monospace', fontWeight: 600 }}>
                  {data.annualized_roi?.toFixed(1) || 'N/A'}%
                </Typography>
              </Box>
              <Box sx={{ textAlign: 'center', border: '1px solid', borderColor: 'divider', p: 1, borderRadius: 1 }}>
                <Typography variant="caption" color="text.secondary" display="block">Strike Price</Typography>
                <Typography variant="h6" color="warning.main" sx={{ fontFamily: 'monospace', fontWeight: 600 }}>
                  ${data.strike?.toFixed(2) || 'N/A'}
                </Typography>
              </Box>
            </Box>

            <Divider sx={{ my: 1.5 }} />

            {/* Option Details */}
            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>Option Details</Typography>
            <Box sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 0.25 }}>
                <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.8rem' }}>Type:</Typography>
                <Chip
                  label={data.option_type?.toUpperCase() || 'N/A'}
                  size="small"
                  color={data.option_type === 'put' ? 'error' : data.option_type === 'call' ? 'success' : 'default'}
                  sx={{ fontSize: '0.7rem', height: 20 }}
                />
              </Box>
              <DataRow label="Expiry Date" value={data.expiry || 'N/A'} />
              <DataRow label="Created At" value={new Date(data.created_at).toLocaleDateString()} />
              <DataRow label="Recommendation ID" value={data.id} />
            </Box>

            {/* Analysis Details */}
            {data.rationale && (
              <>
                <Divider sx={{ my: 1.5 }} />
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>Analysis Details</Typography>
                {typeof data.rationale === 'string' ? (
                  <Typography variant="body2" sx={{ fontStyle: 'italic', p: 1, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
                    {data.rationale}
                  </Typography>
                ) : (
                  <Box>
                    {Object.entries(data.rationale).map(([key, value]) => (
                      <DataRow
                        key={key}
                        label={formatLabel(key)}
                        value={typeof value === 'number' ? value.toFixed(2) : String(value)}
                      />
                    ))}
                  </Box>
                )}
              </>
            )}
          </Box>
        ) : null}
      </Box>
    </Dialog>
  );
}