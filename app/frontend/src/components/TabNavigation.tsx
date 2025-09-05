'use client';

import React from 'react';
import {
  Tabs,
  Tab,
  Box,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  AutoAwesome as RecommendationsIcon,
  AccountBalance as PositionsIcon,
  Assignment as OrdersIcon,
  List as TickersIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';

interface TabNavigationProps {
  value: number;
  onChange: (event: React.SyntheticEvent, newValue: number) => void;
}

const tabs = [
  { label: 'Dashboard', icon: <DashboardIcon /> },
  { label: 'Recommendations', icon: <RecommendationsIcon /> },
  { label: 'Positions', icon: <PositionsIcon /> },
  { label: 'Orders', icon: <OrdersIcon /> },
  { label: 'Tickers', icon: <TickersIcon /> },
  { label: 'Settings', icon: <SettingsIcon /> },
];

export default function TabNavigation({ value, onChange }: TabNavigationProps) {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  return (
    <Box
      sx={{
        borderBottom: 1,
        borderColor: 'divider',
        backgroundColor: 'background.paper',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}
    >
      <Tabs
        value={value}
        onChange={onChange}
        variant={isMobile ? 'scrollable' : 'standard'}
        scrollButtons={isMobile ? 'auto' : false}
        sx={{
          minHeight: 48,
          '& .MuiTab-root': {
            minHeight: 48,
            textTransform: 'none',
            fontSize: '0.875rem',
            fontWeight: 500,
            '&.Mui-selected': {
              color: 'primary.main',
            },
          },
          '& .MuiTabs-indicator': {
            height: 3,
          },
        }}
      >
        {tabs.map((tab, index) => (
          <Tab
            key={tab.label}
            icon={tab.icon}
            label={!isMobile ? tab.label : undefined}
            iconPosition={isMobile ? 'top' : 'start'}
            sx={{
              minWidth: isMobile ? 60 : 120,
              gap: isMobile ? 0 : 1,
            }}
          />
        ))}
      </Tabs>
    </Box>
  );
}