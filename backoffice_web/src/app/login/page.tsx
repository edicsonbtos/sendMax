'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Alert,
  Stack,
  Divider,
  CircularProgress,
} from '@mui/material';

const API_BASE = 'https://api-max-production.up.railway.app';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch(API_BASE + '/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || 'Credenciales invalidas');
      }

      const data = await res.json();

      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('auth_role', data.role);
      localStorage.setItem('auth_name', data.full_name);

      router.push('/');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error de conexion';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: '#FAF8FF',
      }}
    >
      <Card sx={{ maxWidth: 440, width: '100%', mx: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Box sx={{ textAlign: 'center', mb: 3 }}>
            <Box
              component="img"
              src="/logo.png"
              alt="Sendmax"
              sx={{ height: 48, width: 'auto', mb: 2 }}
            />
            <Typography
              variant="h5"
              sx={{ fontWeight: 700, color: '#4B2E83', mb: 0.5 }}
            >
              Sendmax Backoffice
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Ingresa tus credenciales para acceder
            </Typography>
          </Box>

          <Divider sx={{ my: 2 }} />

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <Stack spacing={2.5}>
              <TextField
                fullWidth
                type="email"
                label="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                autoFocus
              />
              <TextField
                fullWidth
                type="password"
                label="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
              <Button
                type="submit"
                variant="contained"
                size="large"
                fullWidth
                disabled={loading || !email || !password}
                sx={{
                  py: 1.5,
                  backgroundColor: '#4B2E83',
                  '&:hover': { backgroundColor: '#3a2366' },
                }}
              >
                {loading ? (
                  <CircularProgress size={24} sx={{ color: '#fff' }} />
                ) : (
                  'Iniciar Sesion'
                )}
              </Button>
            </Stack>
          </form>
        </CardContent>
      </Card>
    </Box>
  );
}
