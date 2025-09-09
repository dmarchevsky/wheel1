# UI Component Library

A consistent set of reusable UI components for the trading application frontend. Built with Material-UI and designed to work seamlessly with the dynamic theme system.

## Overview

This component library provides:
- Consistent styling across the application
- Environment-aware theming (sandbox vs production)
- Reusable patterns for common UI elements
- Type safety with TypeScript
- Accessibility features built-in

## Components

### BaseCard

The foundation card component that all other cards should extend from. Provides consistent styling and environment-aware theming.

```tsx
import { BaseCard } from '@/components/ui';

<BaseCard variant="outlined" environmentAware>
  <CardContent>
    Content here
  </CardContent>
</BaseCard>
```

**Props:**
- `variant`: 'default' | 'outlined' | 'elevated'
- `environmentAware`: boolean - applies sandbox styling when true
- All standard Material-UI Card props

### MetricCard

Pre-built card for displaying key metrics with optional change indicators.

```tsx
import { MetricCard } from '@/components/ui';

<MetricCard
  title="Total Portfolio Value"
  value={125000}
  change={{ value: 2500, percent: 2.04 }}
  loading={false}
/>
```

**Props:**
- `title`: string
- `value`: string | number
- `subtitle?`: string
- `change?`: { value: number, percent: number }
- `loading?`: boolean
- `color?`: 'primary' | 'success' | 'error' | 'warning' | 'info'
- `variant?`: 'default' | 'compact'

### DataTable

Flexible table component with sorting, formatting, and interaction support.

```tsx
import { DataTable, TableColumn } from '@/components/ui';

const columns: TableColumn[] = [
  { id: 'symbol', label: 'Symbol', width: '20%' },
  { id: 'price', label: 'Price', align: 'right', format: (val) => `$${val}` },
];

<DataTable
  columns={columns}
  data={positions}
  onRowClick={(row) => handleRowClick(row)}
  dense
/>
```

**Props:**
- `columns`: TableColumn[] - column definitions
- `data`: any[] - table data
- `loading?`: boolean
- `emptyMessage?`: string
- `dense?`: boolean - compact row height
- `stickyHeader?`: boolean
- `maxHeight?`: number
- `onRowClick?`: (row, index) => void
- `rowProps?`: (row, index) => any

### StatusChip

Consistent status indicators with predefined color schemes.

```tsx
import { StatusChip } from '@/components/ui';

<StatusChip status="success" label="Active" />
<StatusChip status="warning" value="Pending" />
```

**Props:**
- `status`: 'success' | 'error' | 'warning' | 'info' | 'default' | 'pending' | 'completed' | 'failed'
- `value?`: string | number
- All standard Material-UI Chip props

### PnLIndicator

Specialized component for displaying profit/loss values with appropriate colors and icons.

```tsx
import { PnLIndicator } from '@/components/ui';

<PnLIndicator 
  value={1250.50} 
  percentage={2.1} 
  showIcon 
  variant="compact" 
/>
```

**Props:**
- `value`: number - P&L amount
- `percentage?`: number - P&L percentage
- `showIcon?`: boolean - show trend icons
- `showPercentage?`: boolean
- `variant?`: 'default' | 'compact'

### ExpandableCard

Card with collapsible content and customizable header actions.

```tsx
import { ExpandableCard } from '@/components/ui';

<ExpandableCard 
  title="Options Positions" 
  action={<RefreshButton />}
  defaultExpanded={true}
>
  <TableContent />
</ExpandableCard>
```

**Props:**
- `title`: React.ReactNode
- `subtitle?`: React.ReactNode
- `action?`: React.ReactNode - additional header actions
- `defaultExpanded?`: boolean
- `onExpandChange?`: (expanded: boolean) => void
- All BaseCard props

### ActionButton

Enhanced button with loading states and consistent styling.

```tsx
import { ActionButton } from '@/components/ui';

<ActionButton 
  loading={submitting}
  loadingText="Submitting..."
  onClick={handleSubmit}
>
  Submit Trade
</ActionButton>
```

**Props:**
- `loading?`: boolean
- `loadingText?`: string - text to show when loading
- All standard Material-UI Button props

### LoadingState

Standardized loading indicator with optional message.

```tsx
import { LoadingState } from '@/components/ui';

<LoadingState message="Fetching positions..." variant="centered" />
```

**Props:**
- `message?`: string
- `size?`: number - spinner size
- `variant?`: 'centered' | 'inline'

### FilterPanel

Flexible filter panel with multiple input types.

```tsx
import { FilterPanel, FilterConfig } from '@/components/ui';

const filters: FilterConfig[] = [
  { type: 'text', key: 'symbol', label: 'Symbol' },
  { type: 'select', key: 'type', label: 'Type', options: [
    { label: 'Put', value: 'put' },
    { label: 'Call', value: 'call' }
  ]},
  { type: 'range', key: 'score', label: 'Score', min: 0, max: 100 },
];

<FilterPanel 
  filters={filters}
  values={filterValues}
  onChange={handleFilterChange}
  visible={showFilters}
/>
```

**Props:**
- `filters`: FilterConfig[] - filter definitions
- `values`: Record<string, any> - current filter values
- `onChange`: (key: string, value: any) => void
- `onReset?`: () => void
- `visible?`: boolean

## Design Principles

### Consistency
- All components use the same border radius (0 for sharp edges)
- Consistent spacing using Material-UI's spacing system
- Standardized color palette from the theme

### Environment Awareness
- Components automatically adapt styling based on sandbox/production environment
- Orange/amber color scheme for sandbox mode
- Consistent visual indicators across components

### Typography
- Monospace font for financial data (prices, symbols)
- Consistent font weights and sizes
- Proper text hierarchy

### Accessibility
- Proper ARIA labels and roles
- Keyboard navigation support
- Color contrast compliance
- Screen reader friendly

## Usage Guidelines

### Import Pattern
```tsx
// Preferred: Import specific components
import { MetricCard, DataTable } from '@/components/ui';

// Alternative: Import with alias
import { MetricCard as Card } from '@/components/ui';
```

### Styling
- Use the `sx` prop for component-specific styling
- Leverage theme colors instead of hardcoded values
- Maintain consistent spacing patterns

### Data Formatting
- Currency values are auto-formatted in DataTable
- Use PnLIndicator for profit/loss displays
- StatusChip for status indicators

## Migration Guide

To migrate existing components to use the library:

1. Replace custom card implementations with `BaseCard` or `MetricCard`
2. Use `DataTable` instead of custom table implementations
3. Replace loading states with `LoadingState` component
4. Use `StatusChip` for consistent status displays
5. Migrate expandable sections to `ExpandableCard`

## Examples

See individual component files for detailed examples and prop documentation.