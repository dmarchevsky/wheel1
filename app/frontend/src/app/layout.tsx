'use client'

import React, { useState } from 'react'
import { Inter } from 'next/font/google'
import CssBaseline from '@mui/material/CssBaseline'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns'
import { Box, useTheme, useMediaQuery } from '@mui/material'
import SideMenu, { MobileMenuToggle } from '@/components/SideMenu'
import AccountHeader from '@/components/AccountHeader'
import { DynamicThemeProvider } from '@/contexts/ThemeContext'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

const DRAWER_WIDTH = 240;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const muiTheme = useTheme();
  const isMobile = useMediaQuery(muiTheme.breakpoints.down('md'));

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleCollapseToggle = () => {
    setCollapsed(!collapsed);
  };

  return (
    <html lang="en">
      <body className={inter.className} suppressHydrationWarning={true}>
        <DynamicThemeProvider>
          <CssBaseline />
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <LayoutContent 
              mobileOpen={mobileOpen}
              collapsed={collapsed}
              handleDrawerToggle={handleDrawerToggle}
              handleCollapseToggle={handleCollapseToggle}
            >
              {children}
            </LayoutContent>
          </LocalizationProvider>
        </DynamicThemeProvider>
      </body>
    </html>
  )
}

// Separate component to use theme hooks
function LayoutContent({ 
  children, 
  mobileOpen, 
  collapsed, 
  handleDrawerToggle, 
  handleCollapseToggle 
}: {
  children: React.ReactNode
  mobileOpen: boolean
  collapsed: boolean
  handleDrawerToggle: () => void
  handleCollapseToggle: () => void
}) {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))

  return (
    <Box sx={{ display: 'flex' }}>
      {/* Side Menu */}
      <SideMenu 
        open={mobileOpen} 
        onToggle={handleDrawerToggle} 
        collapsed={collapsed}
        onCollapseToggle={handleCollapseToggle}
      />
      
      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { md: `calc(100% - ${collapsed ? 64 : DRAWER_WIDTH}px)` },
          ml: { md: `${collapsed ? 64 : DRAWER_WIDTH}px` },
          transition: 'width 0.2s ease-in-out, margin-left 0.2s ease-in-out',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Account Header - shown on all pages */}
        <AccountHeader collapsed={collapsed} />
        
        {/* Page Content */}
        <Box sx={{ flexGrow: 1, px: 3, py: 3 }}>
          {children}
        </Box>
      </Box>
    </Box>
  )
}
