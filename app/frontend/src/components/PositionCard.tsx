'use client'

import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  IconButton,
  Collapse,
  Grid,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
} from '@mui/icons-material'
import { useState } from 'react'
import { Position } from '@/types'

interface PositionCardProps {
  position: Position
}

export default function PositionCard({ position }: PositionCardProps) {
  const [expanded, setExpanded] = useState(false)

  const isProfitable = position.pnl >= 0
  const isPut = position.type === 'PUT'

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box>
            <Typography variant="h6" component="div">
              {position.symbol}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              {position.type} ${position.strike} • {position.quantity} contracts
            </Typography>
          </Box>
          <Box sx={{ textAlign: 'right' }}>
            <Typography
              variant="h6"
              color={isProfitable ? 'success.main' : 'error.main'}
              sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}
            >
              {isProfitable ? <TrendingUpIcon sx={{ mr: 0.5 }} /> : <TrendingDownIcon sx={{ mr: 0.5 }} />}
              ${position.pnl.toFixed(2)}
            </Typography>
            <Typography
              variant="body2"
              color={isProfitable ? 'success.main' : 'error.main'}
            >
              {isProfitable ? '+' : ''}{position.pnlPercent.toFixed(1)}%
            </Typography>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box>
            <Chip
              label={position.type}
              color={isPut ? 'error' : 'success'}
              variant="outlined"
              size="small"
              sx={{ mr: 1 }}
            />
            <Typography variant="body2" color="textSecondary">
              Expires: {new Date(position.expiry).toLocaleDateString()}
            </Typography>
          </Box>
          <IconButton
            onClick={() => setExpanded(!expanded)}
            sx={{
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 0.3s',
            }}
          >
            <ExpandMoreIcon />
          </IconButton>
        </Box>

        <Collapse in={expanded} timeout="auto" unmountOnExit>
          <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid #333' }}>
            <Grid container spacing={2}>
              <Grid item xs={6}>
                <Typography variant="body2" color="textSecondary">
                  Avg Price
                </Typography>
                <Typography variant="body1">
                  ${position.avgPrice.toFixed(2)}
                </Typography>
              </Grid>
              <Grid item xs={6}>
                <Typography variant="body2" color="textSecondary">
                  Current Price
                </Typography>
                <Typography variant="body1">
                  ${position.currentPrice.toFixed(2)}
                </Typography>
              </Grid>
              {position.delta && (
                <Grid item xs={6}>
                  <Typography variant="body2" color="textSecondary">
                    Delta
                  </Typography>
                  <Typography variant="body1">
                    {position.delta.toFixed(3)}
                  </Typography>
                </Grid>
              )}
              {position.iv && (
                <Grid item xs={6}>
                  <Typography variant="body2" color="textSecondary">
                    IV
                  </Typography>
                  <Typography variant="body1">
                    {position.iv.toFixed(1)}%
                  </Typography>
                </Grid>
              )}
            </Grid>
          </Box>
        </Collapse>
      </CardContent>
    </Card>
  )
}

