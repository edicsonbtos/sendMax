'use client';
import { createTheme, type Shadows } from '@mui/material/styles';

const baseShadows = [
  'none',
  '0 1px 3px rgba(0,0,0,.2)',
  '0 2px 6px rgba(0,0,0,.25)',
  '0 4px 12px rgba(0,0,0,.3)',
  '0 8px 24px rgba(0,0,0,.35)',
  '0 12px 32px rgba(0,0,0,.4)',
  '0 16px 40px rgba(0,0,0,.45)',
  '0 20px 48px rgba(0,0,0,.5)',
  '0 24px 56px rgba(0,0,0,.55)',
  ...Array(16).fill('0 24px 56px rgba(0,0,0,.55)'),
] as Shadows;

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#0052FF',
      light: '#3375FF',
      dark: '#003BB2',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#2E3B55',
      light: '#4F6182',
      dark: '#1C2436',
    },
    background: {
      default: '#F5F7FA',
      paper: '#FFFFFF',
    },
    success: { main: '#00BA88' },
    warning: { main: '#F4B740' },
    error: { main: '#ED4C5C' },
    info: { main: '#0052FF' },
    text: {
      primary: '#1A1A1A',
      secondary: '#4A4A4A',
      disabled: '#9CA3AF',
    },
    divider: 'rgba(0, 0, 0, 0.08)',
  },
  typography: {
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    h1: { fontWeight: 700, letterSpacing: '-0.02em', color: '#1A1A1A' },
    h2: { fontWeight: 700, letterSpacing: '-0.02em', color: '#1A1A1A' },
    h3: { fontWeight: 700, letterSpacing: '-0.01em', color: '#1A1A1A' },
    h4: { fontWeight: 700, letterSpacing: '-0.01em', color: '#1A1A1A' },
    h5: { fontWeight: 600, color: '#1A1A1A' },
    h6: { fontWeight: 600, color: '#1A1A1A' },
    subtitle1: { fontWeight: 500, color: '#4A4A4A' },
    subtitle2: { fontWeight: 500, color: '#9CA3AF' },
    body1: { fontSize: '0.9375rem', lineHeight: 1.6 },
    body2: { fontSize: '0.8125rem', lineHeight: 1.5 },
    caption: { fontSize: '0.75rem', color: '#9CA3AF' },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  shape: {
    borderRadius: 12,
  },
  shadows: baseShadows,
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: '#F5F7FA',
          color: '#1A1A1A',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: '#FFFFFF',
          borderRadius: 16,
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
          border: '1px solid rgba(0, 0, 0, 0.05)',
          transition: 'box-shadow 0.2s ease, transform 0.2s ease',
          '&:hover': {
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04)',
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          padding: '10px 24px',
          fontWeight: 600,
          fontSize: '0.875rem',
        },
        contained: {
          boxShadow: '0 2px 4px rgba(0, 82, 255, 0.2)',
          '&:hover': {
            boxShadow: '0 4px 8px rgba(0, 82, 255, 0.3)',
          },
        },
        outlined: {
          borderColor: 'rgba(0, 82, 255, 0.3)',
          color: '#0052FF',
          '&:hover': {
            borderColor: '#0052FF',
            backgroundColor: 'rgba(0, 82, 255, 0.04)',
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 12,
            backgroundColor: '#FAFAFA',
            '& fieldset': {
              borderColor: 'rgba(0, 0, 0, 0.1)',
            },
            '&:hover fieldset': {
              borderColor: 'rgba(0, 0, 0, 0.2)',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#0052FF',
            },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 600,
          fontSize: '0.75rem',
        },
      },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          '& .MuiTableCell-head': {
            backgroundColor: '#F9FAFB',
            fontWeight: 600,
            fontSize: '0.8125rem',
            color: '#6B7280',
            borderBottom: '1px solid rgba(0, 0, 0, 0.08)',
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid rgba(0, 0, 0, 0.04)',
          padding: '14px 16px',
          fontSize: '0.8125rem',
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover': {
            backgroundColor: 'rgba(0, 82, 255, 0.02)',
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 20,
          backgroundColor: '#FFFFFF',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
          border: '1px solid rgba(0, 0, 0, 0.05)',
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: '1px solid rgba(0, 0, 0, 0.08)',
          backgroundColor: '#FFFFFF',
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          borderRadius: 8,
          fontSize: '0.75rem',
          backgroundColor: '#1E293B',
          border: '1px solid rgba(255, 255, 255, 0.1)',
        },
      },
    },
  },
});

export default theme;
