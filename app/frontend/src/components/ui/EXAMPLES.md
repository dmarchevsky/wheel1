# Component Library Examples

This document shows practical examples of how to use the UI component library and migrate existing code.

## Before and After: Refactoring SummaryCard

### Before (Original Implementation)

```tsx
// Original SummaryCard.tsx
import { Card, CardContent, Typography, Box, Skeleton } from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';

export default function SummaryCard({ title, value, subtitle, change, loading = false }) {
  if (loading) {
    return (
      <Card>
        <CardContent>
          <Skeleton variant="text" width="60%" height={24} />
          <Skeleton variant="text" width="40%" height={32} />
          {subtitle && <Skeleton variant="text" width="80%" height={20} />}
        </CardContent>
      </Card>
    );
  }

  const isPositive = change && change.value >= 0;
  const showChange = change !== undefined;

  return (
    <Card>
      <CardContent>
        <Typography color="textSecondary" gutterBottom variant="body2">
          {title}
        </Typography>
        <Typography variant="h4" component="div" 
          color={showChange ? (isPositive ? 'success.main' : 'error.main') : 'text.primary'}
          sx={{ display: 'flex', alignItems: 'center', mb: subtitle ? 1 : 0 }}
        >
          {showChange && (isPositive ? <TrendingUpIcon /> : <TrendingDownIcon />)}
          {typeof value === 'number' && value >= 0 ? `$${value.toLocaleString()}` : value}
        </Typography>
        {subtitle && <Typography variant="body2" color="textSecondary">{subtitle}</Typography>}
        {showChange && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="body2" color={isPositive ? 'success.main' : 'error.main'}>
              {isPositive ? '+' : ''}{change.value >= 0 ? '$' : '-$'}{Math.abs(change.value).toLocaleString()} 
              ({isPositive ? '+' : ''}{change.percent.toFixed(1)}%)
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
```

### After (Using Component Library)

```tsx
// Refactored using MetricCard
import { MetricCard } from '@/components/ui';

export default function SummaryCard(props) {
  return <MetricCard {...props} />;
}
```

**Benefits of refactoring:**
- 90% less code
- Consistent styling automatically applied
- Environment-aware theming
- Better TypeScript support
- Standardized loading states

## Position Table Refactoring

### Before (Custom Table Implementation)

```tsx
// Original table in PositionsTab.tsx
<TableContainer component={Paper} elevation={0} sx={{ borderRadius: 0 }}>
  <Table size="small">
    <TableHead>
      <TableRow>
        <TableCell>Symbol</TableCell>
        <TableCell align="right">Quantity</TableCell>
        <TableCell align="right">P&L</TableCell>
      </TableRow>
    </TableHead>
    <TableBody>
      {positions.map((position, index) => (
        <TableRow key={index}>
          <TableCell>
            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
              {position.symbol}
            </Typography>
          </TableCell>
          <TableCell align="right">{position.quantity}</TableCell>
          <TableCell align="right">
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {position.pnl > 0 ? <TrendingUpIcon color="success" /> : 
               position.pnl < 0 ? <TrendingDownIcon color="error" /> : null}
              <Typography sx={{ color: position.pnl > 0 ? 'success.main' : 'error.main' }}>
                {formatCurrency(position.pnl)}
              </Typography>
            </Box>
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  </Table>
</TableContainer>
```

### After (Using Component Library)

```tsx
// Refactored using DataTable and PnLIndicator
import { DataTable, PnLIndicator, TableColumn } from '@/components/ui';

const columns: TableColumn[] = [
  { id: 'symbol', label: 'Symbol', width: '30%' },
  { id: 'quantity', label: 'Quantity', align: 'right', width: '20%' },
  { 
    id: 'pnl', 
    label: 'P&L', 
    align: 'right', 
    width: '25%',
    format: (value, row) => (
      <PnLIndicator 
        value={value} 
        percentage={row.pnl_percent} 
        variant="compact" 
      />
    )
  },
];

<DataTable
  columns={columns}
  data={positions}
  loading={loading}
  emptyMessage="No positions found"
  dense
/>
```

## Complete Component Migration Example

### Before: Custom ExpandableSection

```tsx
// Custom expandable section
const [expanded, setExpanded] = useState(true);

return (
  <Card sx={{ borderRadius: 0 }}>
    <CardHeader
      title={`Stock Positions (${positions.length})`}
      action={
        <IconButton onClick={() => setExpanded(!expanded)}>
          {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </IconButton>
      }
    />
    <Collapse in={expanded}>
      <CardContent>
        {/* Table content */}
      </CardContent>
    </Collapse>
  </Card>
);
```

### After: Using ExpandableCard

```tsx
import { ExpandableCard, DataTable, ActionButton } from '@/components/ui';

<ExpandableCard
  title={`Stock Positions (${positions.length})`}
  action={
    <ActionButton 
      onClick={handleRefresh} 
      loading={loading}
      size="small"
      variant="outlined"
    >
      Refresh
    </ActionButton>
  }
  defaultExpanded={true}
>
  <DataTable
    columns={stockColumns}
    data={stockPositions}
    loading={loading}
    onRowClick={handlePositionClick}
  />
</ExpandableCard>
```

## Advanced Usage: Custom Themes

### Environment-Aware Styling

```tsx
import { BaseCard } from '@/components/ui';
import { useThemeContext } from '@/contexts/ThemeContext';

function CustomCard() {
  const { environment } = useThemeContext();
  
  return (
    <BaseCard 
      environmentAware 
      sx={{
        // Additional custom styling that works with environment theming
        ...(environment === 'sandbox' && {
          boxShadow: '0 0 10px rgba(255, 152, 0, 0.3)',
        }),
      }}
    >
      <CardContent>
        Environment-aware content
      </CardContent>
    </BaseCard>
  );
}
```

### Complex Filter Example

```tsx
import { FilterPanel, FilterConfig } from '@/components/ui';

const recommendationFilters: FilterConfig[] = [
  {
    type: 'text',
    key: 'symbol',
    label: 'Symbol',
    placeholder: 'e.g., AAPL, MSFT',
  },
  {
    type: 'select',
    key: 'option_type',
    label: 'Option Type',
    options: [
      { label: 'Put Options', value: 'put' },
      { label: 'Call Options', value: 'call' },
    ],
  },
  {
    type: 'range',
    key: 'score_range',
    label: 'Score Range',
    min: 0,
    max: 100,
    step: 5,
  },
  {
    type: 'number',
    key: 'max_collateral',
    label: 'Max Collateral',
    min: 0,
    step: 1000,
  },
];

function RecommendationsWithFilters() {
  const [filters, setFilters] = useState({
    symbol: '',
    option_type: '',
    score_range: [70, 100],
    max_collateral: 50000,
  });

  const handleFilterChange = (key: string, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  return (
    <>
      <FilterPanel
        filters={recommendationFilters}
        values={filters}
        onChange={handleFilterChange}
        visible={showFilters}
      />
      
      <DataTable
        columns={recommendationColumns}
        data={filteredRecommendations}
        onRowClick={handleRecommendationClick}
      />
    </>
  );
}
```

## Migration Checklist

When migrating existing components:

- [ ] Replace `Card` with `BaseCard` or `MetricCard`
- [ ] Replace custom tables with `DataTable`
- [ ] Use `StatusChip` for status indicators
- [ ] Replace P&L displays with `PnLIndicator`
- [ ] Use `LoadingState` for loading indicators
- [ ] Replace buttons with `ActionButton` for consistent styling
- [ ] Use `ExpandableCard` for collapsible sections
- [ ] Implement `FilterPanel` for filter interfaces
- [ ] Update imports to use the component library
- [ ] Remove duplicate styling code
- [ ] Test with both sandbox and production themes

## Performance Considerations

- Components are tree-shakeable - only import what you use
- All components are memoized where appropriate
- Lazy loading is supported for large datasets in DataTable
- Filter debouncing is recommended for real-time filtering

## Best Practices

1. **Always use TypeScript types** - Import and use the provided type definitions
2. **Leverage theme colors** - Use theme-based colors instead of hardcoded values  
3. **Consistent spacing** - Use Material-UI's spacing system (sx={{ mb: 2 }})
4. **Environment testing** - Test components in both sandbox and production modes
5. **Accessibility** - Ensure proper labels and keyboard navigation
6. **Loading states** - Always handle loading states appropriately