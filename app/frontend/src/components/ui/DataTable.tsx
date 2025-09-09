'use client';

import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box,
  SxProps,
  Theme,
} from '@mui/material';

export interface TableColumn {
  id: string;
  label: string;
  align?: 'left' | 'center' | 'right';
  minWidth?: number;
  width?: string;
  format?: (value: any) => string | React.ReactNode;
  sortable?: boolean;
}

export interface DataTableProps {
  columns: TableColumn[];
  data: any[];
  loading?: boolean;
  emptyMessage?: string;
  dense?: boolean;
  stickyHeader?: boolean;
  maxHeight?: number;
  onRowClick?: (row: any, index: number) => void;
  rowProps?: (row: any, index: number) => any;
  sx?: SxProps<Theme>;
  showTotals?: boolean;
  totalsData?: { [key: string]: any };
}

export default function DataTable({
  columns,
  data,
  loading = false,
  emptyMessage = 'No data available',
  dense = false,
  stickyHeader = true,
  maxHeight = 400,
  onRowClick,
  rowProps,
  sx = {},
  showTotals = false,
  totalsData = {},
}: DataTableProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const getCellValue = (row: any, column: TableColumn) => {
    const value = row[column.id];
    
    if (column.format) {
      return column.format(value, row);
    }
    
    // Auto-format currency values
    if (typeof value === 'number' && column.id.toLowerCase().includes('price')) {
      return formatCurrency(value);
    }
    
    return value;
  };

  return (
    <TableContainer
      component={Paper}
      elevation={0}
      sx={{
        borderRadius: 0,
        ...sx,
      }}
    >
      <Table
        size={dense ? 'small' : 'medium'}
        stickyHeader={stickyHeader}
        sx={{ minWidth: 0, tableLayout: 'fixed' }}
      >
        <TableHead>
          <TableRow>
            {columns.map((column) => (
              <TableCell
                key={column.id}
                align={column.align}
                sx={{
                  minWidth: column.minWidth,
                  width: column.width,
                  fontWeight: 600,
                  backgroundColor: 'background.default',
                  ...(dense && { fontSize: '0.75rem' }),
                }}
              >
                {column.label}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {loading ? (
            <TableRow>
              <TableCell colSpan={columns.length} align="center">
                <Box sx={{ py: 4 }}>
                  <Typography variant="body2" color="textSecondary">
                    Loading...
                  </Typography>
                </Box>
              </TableCell>
            </TableRow>
          ) : data.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columns.length} align="center">
                <Box sx={{ py: 4 }}>
                  <Typography variant="body2" color="textSecondary">
                    {emptyMessage}
                  </Typography>
                </Box>
              </TableCell>
            </TableRow>
          ) : (
            data.map((row, index) => {
              const additionalProps = rowProps ? rowProps(row, index) : {};
              return (
                <TableRow
                  key={index}
                  hover={!!onRowClick}
                  onClick={onRowClick ? () => onRowClick(row, index) : undefined}
                  sx={{
                    cursor: onRowClick ? 'pointer' : 'default',
                  }}
                  {...additionalProps}
                >
                  {columns.map((column) => (
                    <TableCell
                      key={column.id}
                      align={column.align}
                      sx={{
                        ...(dense && { fontSize: '0.75rem' }),
                      }}
                    >
                      {getCellValue(row, column)}
                    </TableCell>
                  ))}
                </TableRow>
              );
            })
          )}
        </TableBody>
        
        {showTotals && data.length > 0 && (
          <TableBody>
            <TableRow>
              {columns.map((column, index) => (
                <TableCell 
                  key={column.id}
                  align={column.align}
                  sx={{
                    fontWeight: 'bold',
                    borderTop: 2,
                    borderTopColor: 'grey.300',
                    ...(dense && { fontSize: '0.75rem' }),
                  }}
                >
                  {index === 0 ? 'Totals' : (
                    totalsData[column.id] !== undefined ? 
                      (column.format ? column.format(totalsData[column.id], totalsData) : totalsData[column.id]) :
                      ''
                  )}
                </TableCell>
              ))}
            </TableRow>
          </TableBody>
        )}
      </Table>
    </TableContainer>
  );
}