'use client';

import React, { createContext, useContext, useEffect, useMemo, useState, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';

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
  setApiKey: () => { },
  clearApiKey: () => { },
  login: () => { },
  logout: () => { },
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
    const storedToken = localStorage.getItem('auth_token') || localStorage.getItem('token') || localStorage.getItem('admin_token');
    const storedRole = localStorage.getItem('auth_role');
    const storedName = localStorage.getItem('auth_name');
    const storedApiKey = localStorage.getItem('BACKOFFICE_API_KEY') || localStorage.getItem('api_key');

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
    localStorage.setItem('admin_token', newToken);
    localStorage.setItem('auth_role', newRole);
    localStorage.setItem('admin_user', newName); // Keeping backwards compat with custom keys depending on the endpoint response
    localStorage.setItem('auth_token', newToken);
    localStorage.setItem('auth_name', newName);
    setToken(newToken);
    setRole(newRole);
    setFullName(newName);
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_role');
    localStorage.removeItem('auth_name');
    localStorage.removeItem('admin_token');
    localStorage.removeItem('token');
    localStorage.removeItem('admin_user');
    setToken(null);
    setRole(null);
    setFullName(null);
    router.push('/login');
  };

  const setApiKey = (key: string) => {
    localStorage.setItem('BACKOFFICE_API_KEY', key);
    localStorage.setItem('api_key', key);
    setApiKeyState(key);
  };

  const clearApiKey = () => {
    localStorage.removeItem('BACKOFFICE_API_KEY');
    localStorage.removeItem('api_key');
    setApiKeyState(null);
    logout(); // Generally, clearing api key triggers logout flow in this app
  };

  const value = useMemo(
    () => ({ token, role, fullName, apiKey, setApiKey, clearApiKey, login, logout, isReady }),
    [token, role, fullName, apiKey, isReady]
  );

  if (!isReady) {
    return (
      <div className="flex justify-center items-center h-screen bg-[#0a0f1e]">
        <div className="w-12 h-12 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
