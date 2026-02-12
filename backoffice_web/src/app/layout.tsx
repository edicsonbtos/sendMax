import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AppRouterCacheProvider } from '@mui/material-nextjs/v15-appRouter';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import theme from './theme';
import Sidebar from '@/components/Sidebar';
import { AuthProvider } from '@/components/AuthProvider';

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Sendmax Backoffice",
  description: "Panel de administracion Sendmax - Gestion de ordenes, billeteras y cierres",
  icons: {
    icon: "/logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={inter.variable}>
      <body className={inter.className}>
        <AppRouterCacheProvider>
          <ThemeProvider theme={theme}>
            <CssBaseline />
            <AuthProvider>
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Sidebar />
                <Box
                  component="main"
                  sx={{
                    flexGrow: 1,
                    backgroundColor: 'background.default',
                    minHeight: '100vh',
                    overflow: 'auto',
                    width: { xs: '100%', md: 'calc(100% - 264px)' },
                  }}
                >
                  <Box
                    sx={{
                      maxWidth: 1400,
                      mx: 'auto',
                      p: { xs: 2, sm: 3, md: 4 },
                      pt: { xs: 7, sm: 4 },
                    }}
                  >
                    {children}
                  </Box>
                </Box>
              </Box>
            </AuthProvider>
          </ThemeProvider>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
