'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Box, Card, CardContent, Typography, TextField, Button, Alert, Stack, Divider, CircularProgress } from '@mui/material';
import { useAuth } from '@/components/AuthProvider';
import { apiPost } from '@/lib/api';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const data = await apiPost<{
        access_token: string;
        role: string;
        full_name: string;
      }>('/auth/login', { email, password });

      login(data.access_token, data.role, data.full_name);

      if (data.role === 'admin' || data.role === 'superadmin') {
        router.push('/admin');
      } else {
        router.push('/operator-office');
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error de conexion');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', backgroundColor: '#FAF8FF' }}>
      <Card sx={{ maxWidth: 440, width: '100%', mx: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Box sx={{ textAlign: 'center', mb: 3 }}>
            <Box component="img" src="/logo.png" alt="Sendmax" sx={{ height: 48, width: 'auto', mb: 2 }} />
            <Typography variant="h5" sx={{ fontWeight: 700, color: '#4B2E83', mb: 0.5 }}>Sendmax Backoffice</Typography>
            <Typography variant="body2" color="text.secondary">Ingresa tus credenciales para acceder</Typography>
          </Box>
          <Divider sx={{ my: 2 }} />
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          <form onSubmit={handleSubmit}>
            <Stack spacing={2.5}>
              <TextField fullWidth type="email" label="Email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" autoFocus />
              <TextField fullWidth type="password" label="Password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
              <Button type="submit" variant="contained" size="large" fullWidth disabled={loading || !email || !password}
                sx={{ py: 1.5, backgroundColor: '#4B2E83', '&:hover': { backgroundColor: '#3a2366' } }}>
                {loading ? <CircularProgress size={24} sx={{ color: '#fff' }} /> : 'Iniciar Sesion'}
              </Button>
            </Stack>
          </form>
        </CardContent>
      </Card>
    </Box>
  );
}
