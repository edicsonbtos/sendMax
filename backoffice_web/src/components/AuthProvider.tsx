'use client';

import React, { createContext, useContext, useEffect, useMemo, useRef, useState, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Box, CircularProgress } from '@mui/material';

interface AuthContextType {
  apiKey: string | null;
  setApiKey: (key: string) => void;
  clearApiKey: () => void;
  isReady: boolean;
}

const AuthContext = createContext<AuthContextType>({
  apiKey: null,
  setApiKey: () => {},
  clearApiKey: () => {},
  isReady: false,
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const redirected = useRef(false);

  // Importante: arrancar en "no listo" para que SSR y primer render del cliente coincidan
  const [isReady, setIsReady] = useState(false);
  const [apiKey, setApiKeyState] = useState<string | null>(null);

  useEffect(() => {
    // Ya estamos en cliente: podemos leer localStorage
    const stored = localStorage.getItem('BACKOFFICE_API_KEY');
    setApiKeyState(stored);
    setIsReady(true);
  }, []);

  useEffect(() => {
    if (!isReady) return;
    if (!apiKey && pathname !== '/' && !redirected.current) {
      redirected.current = true;
      router.push('/');
    }
  }, [isReady, apiKey, pathname, router]);

  const setApiKey = (key: string) => {
    localStorage.setItem('BACKOFFICE_API_KEY', key);
    setApiKeyState(key);
  };

  const clearApiKey = () => {
    localStorage.removeItem('BACKOFFICE_API_KEY');
    setApiKeyState(null);
    router.push('/');
  };

  const value = useMemo(() => ({ apiKey, setApiKey, clearApiKey, isReady }), [apiKey, isReady]);

  // Mientras no está listo, renderizamos SIEMPRE lo mismo (evita mismatch)
  if (!isReady) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          backgroundColor: '#FAF8FF',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}