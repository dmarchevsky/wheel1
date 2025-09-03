'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { createTheme, ThemeProvider, Theme } from '@mui/material/styles';
import { TradingEnvironment } from '@/types';
import { tradingEnvironmentApi } from '@/lib/api';

interface ThemeContextType {
  environment: TradingEnvironment;
  setEnvironment: (env: TradingEnvironment) => void;
  isDark: boolean;
  toggleDarkMode: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const useThemeContext = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useThemeContext must be used within a DynamicThemeProvider');
  }
  return context;
};

interface DynamicThemeProviderProps {
  children: ReactNode;
}

export function DynamicThemeProvider({ children }: DynamicThemeProviderProps) {
  const [environment, setEnvironment] = useState<TradingEnvironment>('production');
  const [isDark, setIsDark] = useState(true); // Default to dark mode

  // Fetch environment on mount
  useEffect(() => {
    const fetchEnvironment = async () => {
      try {
        const response = await tradingEnvironmentApi.getStatus();
        setEnvironment(response.data.current_environment);
      } catch (error) {
        console.error('Failed to fetch environment status:', error);
      }
    };

    fetchEnvironment();
  }, []);

  const toggleDarkMode = () => {
    setIsDark(!isDark);
  };

  // Create theme based on environment and dark mode preference
  const theme = createTheme({
    palette: {
      mode: isDark ? 'dark' : 'light',
      primary: {
        main: environment === 'sandbox' ? '#ff9800' : '#00d4aa', // Orange for sandbox, teal for production
      },
      secondary: {
        main: '#ff6b6b',
      },
      background: {
        default: environment === 'sandbox' 
          ? (isDark ? '#0f0a00' : '#fff8e1') // Darker orange tint for sandbox
          : (isDark ? '#0a0a0a' : '#f5f5f5'), // Standard dark/light
        paper: environment === 'sandbox'
          ? (isDark ? '#1f1000' : '#ffecb3') // Orange-tinted paper for sandbox
          : (isDark ? '#1a1a1a' : '#ffffff'), // Standard paper
      },
      text: {
        primary: isDark ? '#ffffff' : '#000000',
        secondary: isDark ? '#b0b0b0' : '#666666',
      },
      warning: {
        main: '#ff9800',
        light: '#ffb74d',
        dark: '#f57c00',
      },
      success: {
        main: '#4caf50',
        light: '#81c784',
        dark: '#388e3c',
      },
      error: {
        main: '#f44336',
        light: '#e57373',
        dark: '#d32f2f',
      },
    },
    typography: {
      fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif',
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
            border: environment === 'sandbox' 
              ? '1px solid rgba(255, 152, 0, 0.3)' // Orange border for sandbox
              : '1px solid #333',
            backgroundColor: environment === 'sandbox'
              ? (isDark ? 'rgba(31, 16, 0, 0.8)' : 'rgba(255, 248, 225, 0.8)')
              : undefined,
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          root: {
            borderRadius: 12,
            ...(environment === 'sandbox' && {
              backgroundColor: isDark ? 'rgba(31, 16, 0, 0.9)' : 'rgba(255, 236, 179, 0.9)',
              border: '1px solid rgba(255, 152, 0, 0.2)',
            }),
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: {
            ...(environment === 'sandbox' && {
              backgroundColor: isDark ? '#2d1a00' : '#fff3c4',
              borderBottom: '1px solid #ff9800',
            }),
          },
        },
      },
    },
  });

  const contextValue: ThemeContextType = {
    environment,
    setEnvironment,
    isDark,
    toggleDarkMode,
  };

  return (
    <ThemeContext.Provider value={contextValue}>
      <ThemeProvider theme={theme}>
        {children}
      </ThemeProvider>
    </ThemeContext.Provider>
  );
}
