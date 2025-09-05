'use client'

import React, { useState } from 'react'
import {
  Box,
  Card,
  CardHeader,
  CardContent,
  Typography,
  IconButton,
  Collapse,
} from '@mui/material'
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material'
import PositionsSummary from '@/components/PositionsSummary'
import RecentActivity from '@/components/RecentActivity'

export default function DashboardTab() {
  const [portfolioExpanded, setPortfolioExpanded] = useState(true)
  const [activityExpanded, setActivityExpanded] = useState(true)

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Portfolio Summary */}
      <Card sx={{ borderRadius: 0 }}>
        <CardHeader
          title="Portfolio Summary"
          action={
            <IconButton
              onClick={() => setPortfolioExpanded(!portfolioExpanded)}
              sx={{ borderRadius: 0 }}
            >
              {portfolioExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          }
        />
        <Collapse in={portfolioExpanded}>
          <CardContent sx={{ pt: 0 }}>
            <PositionsSummary />
          </CardContent>
        </Collapse>
      </Card>
      
      {/* Recent Activity */}
      <Card sx={{ borderRadius: 0 }}>
        <CardHeader
          title="Recent Activity"
          action={
            <IconButton
              onClick={() => setActivityExpanded(!activityExpanded)}
              sx={{ borderRadius: 0 }}
            >
              {activityExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          }
        />
        <Collapse in={activityExpanded}>
          <CardContent sx={{ pt: 0 }}>
            <RecentActivity />
          </CardContent>
        </Collapse>
      </Card>
    </Box>
  )
}