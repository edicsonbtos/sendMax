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
    mode: 'dark',
    primary: {
      main: '#00E5FF',
      light: '#33E9FF',
      dark: '#00B2CC',
      contrastText: '#050505',
    },
    secondary: {
      main: '#7B2FBE',
      light: '#9558CB',
      dark: '#562185',
    },
    background: {
      default: '#050505',
      paper: '#0a0a0a',
    },
    success: { main: '#00c896' },
    warning: { main: '#f9c74f' },
    error: { main: '#ff6b6b' },
    info: { main: '#2563EB' },
    text: {
      primary: '#e0e0e0',
      secondary: '#a0a0a0',
      disabled: '#555555',
    },
    divider: 'rgba(0, 229, 255, 0.1)',
  },
  typography: {
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    h1: { fontWeight: 700, letterSpacing: '-0.02em', color: '#fff' },
    h2: { fontWeight: 700, letterSpacing: '-0.02em', color: '#fff' },
    h3: { fontWeight: 700, letterSpacing: '-0.01em', color: '#fff' },
    h4: { fontWeight: 700, letterSpacing: '-0.01em', color: '#fff' },
    h5: { fontWeight: 600, color: '#fff' },
    h6: { fontWeight: 600, color: '#fff' },
    subtitle1: { fontWeight: 500, color: '#a0a0a0' },
    subtitle2: { fontWeight: 500, color: '#555555' },
    body1: { fontSize: '0.9375rem', lineHeight: 1.6 },
    body2: { fontSize: '0.8125rem', lineHeight: 1.5 },
    caption: { fontSize: '0.75rem', color: '#555555' },
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
          backgroundColor: '#050505',
          color: '#e0e0e0',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(255, 255, 255, 0.03)',
          backdropFilter: 'blur(10px)',
          borderRadius: 16,
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          border: '1px solid rgba(0,229,255,0.1)',
          transition: 'box-shadow 0.2s ease, transform 0.2s ease',
          '&:hover': {
            boxShadow: '0 8px 32px rgba(0, 229, 255, 0.15)',
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
          boxShadow: '0 2px 8px rgba(0,229,255,.25)',
          '&:hover': {
            boxShadow: '0 4px 16px rgba(0,229,255,.35)',
          },
        },
        outlined: {
          borderColor: 'rgba(0,229,255,0.3)',
          color: '#00E5FF',
          '&:hover': {
            borderColor: '#00E5FF',
            backgroundColor: 'rgba(0,229,255,0.08)',
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 12,
            '& fieldset': {
              borderColor: 'rgba(0,229,255,0.2)',
            },
            '&:hover fieldset': {
              borderColor: 'rgba(0,229,255,0.4)',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#00E5FF',
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
            backgroundColor: '#0a0a0a',
            fontWeight: 600,
            fontSize: '0.8125rem',
            color: 'rgba(0,229,255,0.7)',
            borderBottom: '1px solid rgba(0,229,255,0.15)',
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          padding: '14px 16px',
          fontSize: '0.8125rem',
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover': {
            backgroundColor: 'rgba(0,229,255,0.04)',
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 20,
          backgroundColor: '#0a0a0a',
          boxShadow: '0 16px 40px rgba(0,0,0,.6)',
          border: '1px solid rgba(0,229,255,0.1)',
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
          borderRight: '1px solid rgba(0,229,255,0.1)',
          backgroundColor: '#0a0a0a',
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          borderRadius: 8,
          fontSize: '0.75rem',
          backgroundColor: '#111',
          border: '1px solid rgba(0,229,255,0.2)',
        },
      },
    },
  },
});

export default theme;
