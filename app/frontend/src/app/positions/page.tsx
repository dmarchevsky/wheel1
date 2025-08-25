'use client'

import { useState, useEffect } from 'react'
import {
  Box,
  Container,
  Grid,
  Typography,
  Card,
  CardContent,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
} from '@mui/material'
import {
  Add as AddIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material'
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid'
import { Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material'
import PositionCard from '@/components/PositionCard'
import { Position } from '@/types'
import { positionsApi } from '@/lib/api'

// Mock data
const mockPositions: Position[] = [
  {
    id: 1,
    symbol: 'AAPL',
    type: 'PUT',
    strike: 150,
    expiry: '2024-01-19',
    quantity: 1,
    avgPrice: 2.50,
    currentPrice: 2.75,
    pnl: 25.00,
    pnlPercent: 10.0,
    delta: -0.45,
    gamma: 0.02,
    theta: -0.15,
    vega: 0.08,
    iv: 25.5,
  },
  {
    id: 2,
    symbol: 'TSLA',
    type: 'CALL',
    strike: 200,
    expiry: '2024-01-26',
    quantity: 2,
    avgPrice: 1.80,
    currentPrice: 1.60,
    pnl: -40.00,
    pnlPercent: -11.1,
    delta: 0.65,
    gamma: 0.03,
    theta: -0.20,
    vega: 0.12,
    iv: 35.2,
  },
  {
    id: 3,
    symbol: 'NVDA',
    type: 'PUT',
    strike: 450,
    expiry: '2024-02-02',
    quantity: 1,
    avgPrice: 3.20,
    currentPrice: 3.45,
    pnl: 25.00,
    pnlPercent: 7.8,
    delta: -0.30,
    gamma: 0.01,
    theta: -0.10,
    vega: 0.06,
    iv: 28.1,
  },
]

const columns: GridColDef[] = [
  { field: 'symbol', headerName: 'Symbol', width: 100 },
  { field: 'type', headerName: 'Type', width: 80 },
  { field: 'strike', headerName: 'Strike', width: 100, type: 'number' },
  { field: 'expiry', headerName: 'Expiry', width: 120 },
  { field: 'quantity', headerName: 'Qty', width: 80, type: 'number' },
  { field: 'avgPrice', headerName: 'Avg Price', width: 120, type: 'number' },
  { field: 'currentPrice', headerName: 'Current', width: 120, type: 'number' },
  {
    field: 'pnl',
    headerName: 'P&L',
    width: 120,
    type: 'number',
    renderCell: (params) => (
      <Typography
        color={params.value >= 0 ? 'success.main' : 'error.main'}
        fontWeight="bold"
      >
        ${params.value.toFixed(2)}
      </Typography>
    ),
  },
  {
    field: 'pnlPercent',
    headerName: 'P&L %',
    width: 100,
    type: 'number',
    renderCell: (params) => (
      <Typography
        color={params.value >= 0 ? 'success.main' : 'error.main'}
        fontWeight="bold"
      >
        {params.value >= 0 ? '+' : ''}{params.value.toFixed(1)}%
      </Typography>
    ),
  },
  {
    field: 'actions',
    type: 'actions',
    headerName: 'Actions',
    width: 120,
    getActions: (params) => [
      <GridActionsCellItem
        key="edit"
        icon={<EditIcon />}
        label="Edit"
        onClick={() => console.log('Edit', params.id)}
      />,
      <GridActionsCellItem
        key="delete"
        icon={<DeleteIcon />}
        label="Delete"
        onClick={() => console.log('Delete', params.id)}
      />,
    ],
  },
]

export default function PositionsPage() {
  const [positions, setPositions] = useState<Position[]>(mockPositions)
  const [loading, setLoading] = useState(false)
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('table')
  const [openDialog, setOpenDialog] = useState(false)
  const [filter, setFilter] = useState('')

  const filteredPositions = positions.filter(position =>
    position.symbol.toLowerCase().includes(filter.toLowerCase()) ||
    position.type.toLowerCase().includes(filter.toLowerCase())
  )

  const totalPnl = positions.reduce((sum, pos) => sum + pos.pnl, 0)
  const totalPnlPercent = positions.length > 0 
    ? (totalPnl / positions.reduce((sum, pos) => sum + pos.avgPrice * pos.quantity, 0)) * 100
    : 0

  const handleAddPosition = () => {
    setOpenDialog(true)
  }

  const handleCloseDialog = () => {
    setOpenDialog(false)
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1">
          Positions
        </Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant={viewMode === 'table' ? 'contained' : 'outlined'}
            onClick={() => setViewMode('table')}
          >
            Table View
          </Button>
          <Button
            variant={viewMode === 'grid' ? 'contained' : 'outlined'}
            onClick={() => setViewMode('grid')}
          >
            Card View
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleAddPosition}
          >
            Add Position
          </Button>
        </Box>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total P&L
              </Typography>
              <Typography variant="h4" component="div" color={totalPnl >= 0 ? 'success.main' : 'error.main'}>
                ${totalPnl.toFixed(2)}
              </Typography>
              <Typography variant="body2" color={totalPnlPercent >= 0 ? 'success.main' : 'error.main'}>
                {totalPnlPercent >= 0 ? '+' : ''}{totalPnlPercent.toFixed(1)}%
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Positions
              </Typography>
              <Typography variant="h4" component="div">
                {positions.length}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Active contracts
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Winning Positions
              </Typography>
              <Typography variant="h4" component="div" color="success.main">
                {positions.filter(p => p.pnl > 0).length}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Profitable trades
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Win Rate
              </Typography>
              <Typography variant="h4" component="div">
                {positions.length > 0 
                  ? ((positions.filter(p => p.pnl > 0).length / positions.length) * 100).toFixed(1)
                  : 0}%
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Success rate
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filter */}
      <Box sx={{ mb: 3 }}>
        <TextField
          label="Filter positions"
          variant="outlined"
          size="small"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          sx={{ width: 300 }}
        />
      </Box>

      {/* Content */}
      {viewMode === 'table' ? (
        <Card>
          <CardContent>
            <Box sx={{ height: 600, width: '100%' }}>
                                  <DataGrid
                      rows={filteredPositions}
                      columns={columns}
                      initialState={{
                        pagination: {
                          paginationModel: { pageSize: 10 },
                        },
                      }}
                      pageSizeOptions={[10, 25, 50]}
                      disableRowSelectionOnClick
                      sx={{
                        '& .MuiDataGrid-cell': {
                          borderBottom: '1px solid #333',
                        },
                        '& .MuiDataGrid-columnHeaders': {
                          backgroundColor: '#1a1a1a',
                          borderBottom: '2px solid #333',
                        },
                      }}
                    />
            </Box>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {filteredPositions.map((position) => (
            <Grid item xs={12} md={6} lg={4} key={position.id}>
              <PositionCard position={position} />
            </Grid>
          ))}
        </Grid>
      )}

      {/* Add Position Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Add New Position</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Symbol"
                fullWidth
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl fullWidth required>
                <InputLabel>Type</InputLabel>
                <Select label="Type">
                  <MenuItem value="PUT">PUT</MenuItem>
                  <MenuItem value="CALL">CALL</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Strike Price"
                type="number"
                fullWidth
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Expiry Date"
                type="date"
                fullWidth
                required
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Quantity"
                type="number"
                fullWidth
                required
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                label="Average Price"
                type="number"
                fullWidth
                required
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button variant="contained" onClick={handleCloseDialog}>
            Add Position
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  )
}
