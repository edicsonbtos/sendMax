'use client';

import React, { createContext, useContext, useEffect, useMemo, useState, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Box, CircularProgress } from '@mui/material';

interface AuthContextType {
  token: string | null;
  role: string | null;
  fullName: string | null;
  apiKey: string | null;
  setApiKey: (key: string) => void;
  clearApiKey: () => void;
  login: (token: string, role: string, name: string) => void;
  logout: () => void;
  isReady: boolean;
}

const AuthContext = createContext<AuthContextType>({
  token: null,
  role: null,
  fullName: null,
  apiKey: null,
  setApiKey: () => {},
  clearApiKey: () => {},
  login: () => {},
  logout: () => {},
  isReady: false,
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();

  const [isReady, setIsReady] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [fullName, setFullName] = useState<string | null>(null);
  const [apiKey, setApiKeyState] = useState<string | null>(null);

  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    const storedRole = localStorage.getItem('auth_role');
    const storedName = localStorage.getItem('auth_name');
    const storedApiKey = localStorage.getItem('BACKOFFICE_API_KEY');

    setToken(storedToken);
    setRole(storedRole);
    setFullName(storedName);
    setApiKeyState(storedApiKey);
    setIsReady(true);

    if (typeof window !== 'undefined') {
      console.log("AuthProvider: API_URL detectada:", process.env.NEXT_PUBLIC_API_URL);
    }
  }, []);

  useEffect(() => {
    if (!isReady) return;
    if (!token && pathname !== '/login') {
      router.push('/login');
    }
  }, [isReady, token, pathname, router]);

  const login = (newToken: string, newRole: string, newName: string) => {
    localStorage.setItem('auth_token', newToken);
    localStorage.setItem('auth_role', newRole);
    localStorage.setItem('auth_name', newName);
    setToken(newToken);
    setRole(newRole);
    setFullName(newName);
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_role');
    localStorage.removeItem('auth_name');
    setToken(null);
    setRole(null);
    setFullName(null);
    router.push('/login');
  };

  const setApiKey = (key: string) => {
    localStorage.setItem('BACKOFFICE_API_KEY', key);
    setApiKeyState(key);
  };

  const clearApiKey = () => {
    localStorage.removeItem('BACKOFFICE_API_KEY');
    setApiKeyState(null);
    logout();
  };

  const value = useMemo(
    () => ({ token, role, fullName, apiKey, setApiKey, clearApiKey, login, logout, isReady }),
    [token, role, fullName, apiKey, isReady]
  );

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
