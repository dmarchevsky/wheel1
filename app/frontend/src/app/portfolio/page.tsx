'use client'

import React from 'react'
import {
  Container,
  Typography,
  Box,
} from '@mui/material'
import Portfolio from '@/components/Portfolio'

export default function PortfolioPage() {
  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Box mb={3}>
        <Typography variant="h4" component="h1" fontWeight="bold" gutterBottom>
          Portfolio
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Real-time view of your stock and options positions from Tradier
        </Typography>
      </Box>
      
      <Portfolio />
    </Container>
  )
}
