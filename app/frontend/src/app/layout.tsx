'use client'

import React, { useState } from 'react'
import { Inter } from 'next/font/google'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns'
import { AppBar, Toolbar, Typography, Box, useTheme, useMediaQuery } from '@mui/material'
import SideMenu, { MobileMenuToggle } from '@/components/SideMenu'
import AccountHeader from '@/components/AccountHeader'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

// Create a dark theme for the trading application
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#00d4aa',
    },
    secondary: {
      main: '#ff6b6b',
    },
    background: {
      default: '#0a0a0a',
      paper: '#1a1a1a',
    },
    text: {
      primary: '#ffffff',
      secondary: '#b0b0b0',
    },
  },
  typography: {
    fontFamily: inter.style.fontFamily,
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
    },
    h3: {
      fontSize: '1.5rem',
      fontWeight: 600,
    },
    h4: {
      fontSize: '1.25rem',
      fontWeight: 600,
    },
    h5: {
      fontSize: '1.125rem',
      fontWeight: 600,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          border: '1px solid #333',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
      },
    },
  },
})

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
        <ThemeProvider theme={darkTheme}>
          <CssBaseline />
          <LocalizationProvider dateAdapter={AdapterDateFns}>
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
          </LocalizationProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
