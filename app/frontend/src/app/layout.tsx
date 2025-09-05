'use client'

import React from 'react'
import { Inter } from 'next/font/google'
import CssBaseline from '@mui/material/CssBaseline'
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider'
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns'
import { Box } from '@mui/material'
import AccountHeader from '@/components/AccountHeader'
import { DynamicThemeProvider } from '@/contexts/ThemeContext'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className} suppressHydrationWarning={true}>
        <DynamicThemeProvider>
          <CssBaseline />
          <LocalizationProvider dateAdapter={AdapterDateFns}>
            <LayoutContent>
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
  children
}: {
  children: React.ReactNode
}) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Account Header - shown on all pages */}
      <AccountHeader />
      
      {/* Page Content */}
      <Box sx={{ flexGrow: 1 }}>
        {children}
      </Box>
    </Box>
  )
}
