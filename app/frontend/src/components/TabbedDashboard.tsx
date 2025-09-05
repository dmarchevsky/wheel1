'use client';

import React, { useState } from 'react';
import { Box, Container } from '@mui/material';
import TabNavigation from './TabNavigation';
import DashboardTab from './tabs/DashboardTab';
import RecommendationsTab from './tabs/RecommendationsTab';
import PositionsTab from './tabs/PositionsTab';
import OrdersTab from './tabs/OrdersTab';
import TickersTab from './tabs/TickersTab';
import SettingsTab from './tabs/SettingsTab';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`dashboard-tabpanel-${index}`}
      aria-labelledby={`dashboard-tab-${index}`}
      {...other}
    >
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

export default function TabbedDashboard() {
  const [currentTab, setCurrentTab] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Tab Navigation */}
      <TabNavigation value={currentTab} onChange={handleTabChange} />

      {/* Tab Content */}
      <Container maxWidth="xl" sx={{ flexGrow: 1, py: 3 }}>
        <TabPanel value={currentTab} index={0}>
          <DashboardTab />
        </TabPanel>
        
        <TabPanel value={currentTab} index={1}>
          <RecommendationsTab />
        </TabPanel>
        
        <TabPanel value={currentTab} index={2}>
          <PositionsTab />
        </TabPanel>
        
        <TabPanel value={currentTab} index={3}>
          <OrdersTab />
        </TabPanel>
        
        <TabPanel value={currentTab} index={4}>
          <TickersTab />
        </TabPanel>
        
        <TabPanel value={currentTab} index={5}>
          <SettingsTab />
        </TabPanel>
      </Container>
    </Box>
  );
}