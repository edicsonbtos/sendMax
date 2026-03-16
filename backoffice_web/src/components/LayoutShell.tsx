'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import { Box } from '@mui/material';
import Sidebar from '@/components/Sidebar';

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === '/login';

  if (isLoginPage) return <>{children}</>;

  return (
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
  );
}
