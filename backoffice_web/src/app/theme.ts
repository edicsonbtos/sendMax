'use client';
import { createTheme, type Shadows } from '@mui/material/styles';

const baseShadows = [
  'none',
  '0 1px 3px rgba(17,24,39,.04)',
  '0 2px 6px rgba(17,24,39,.05)',
  '0 4px 12px rgba(17,24,39,.06)',
  '0 8px 24px rgba(17,24,39,.06)',
  '0 12px 32px rgba(17,24,39,.08)',
  '0 16px 40px rgba(17,24,39,.10)',
  '0 20px 48px rgba(17,24,39,.12)',
  '0 24px 56px rgba(17,24,39,.14)',
  ...Array(16).fill('0 24px 56px rgba(17,24,39,.14)'),
] as Shadows;

const theme = createTheme({
  palette: {
    primary: {
      main: '#4B2E83',
      light: '#6B46C1',
      dark: '#3A2266',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#5A37A0',
      light: '#D8CCFF',
      dark: '#4B2E83',
    },
    background: {
      default: '#FAF8FF',
      paper: '#FFFFFF',
    },
    success: {
      main: '#16A34A',
      light: '#EAF7EF',
    },
    warning: {
      main: '#F59E0B',
      light: '#FFF5E6',
    },
    error: {
      main: '#DC2626',
      light: '#FDECEC',
    },
    info: {
      main: '#2563EB',
      light: '#EAF1FF',
    },
    text: {
      primary: '#111827',
      secondary: '#475569',
      disabled: '#64748B',
    },
    divider: '#E9E3F7',
  },
  typography: {
    fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    h1: { fontWeight: 700, letterSpacing: '-0.02em' },
    h2: { fontWeight: 700, letterSpacing: '-0.02em' },
    h3: { fontWeight: 700, letterSpacing: '-0.01em' },
    h4: { fontWeight: 700, letterSpacing: '-0.01em' },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    subtitle1: { fontWeight: 500, color: '#475569' },
    subtitle2: { fontWeight: 500, color: '#64748B' },
    body1: { fontSize: '0.9375rem', lineHeight: 1.6 },
    body2: { fontSize: '0.8125rem', lineHeight: 1.5 },
    caption: { fontSize: '0.75rem', color: '#64748B' },
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
          backgroundColor: '#FAF8FF',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0 8px 24px rgba(17,24,39,.06)',
          border: '1px solid #E9E3F7',
          transition: 'box-shadow 0.2s ease, transform 0.2s ease',
          '&:hover': {
            boxShadow: '0 12px 32px rgba(17,24,39,.08)',
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
          boxShadow: '0 2px 8px rgba(75,46,131,.25)',
          '&:hover': {
            boxShadow: '0 4px 16px rgba(75,46,131,.35)',
          },
        },
        outlined: {
          borderColor: '#D8CCFF',
          color: '#4B2E83',
          '&:hover': {
            borderColor: '#4B2E83',
            backgroundColor: '#EFEAFF',
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
              borderColor: '#E9E3F7',
            },
            '&:hover fieldset': {
              borderColor: '#D8CCFF',
            },
            '&.Mui-focused fieldset': {
              borderColor: '#4B2E83',
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
            backgroundColor: '#FAF8FF',
            fontWeight: 600,
            fontSize: '0.8125rem',
            color: '#475569',
            borderBottom: '2px solid #E9E3F7',
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid #F3F0FF',
          padding: '14px 16px',
          fontSize: '0.8125rem',
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover': {
            backgroundColor: '#FAF8FF',
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 20,
          boxShadow: '0 16px 40px rgba(17,24,39,.10)',
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
          borderRight: '1px solid #E9E3F7',
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          borderRadius: 8,
          fontSize: '0.75rem',
        },
      },
    },
  },
});

export default theme;
