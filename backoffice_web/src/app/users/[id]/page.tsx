'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Stack,
  Grid,
  CircularProgress,
  Alert,
  IconButton,
  Button,
  Chip,
  Divider,
  Paper,
  Avatar,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  TableHead,
  TableRow,
  MenuItem,
  Tooltip,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  ContentCopy as CopyIcon,
  LockReset as ResetIcon,
  Shield as AdminIcon,
  SupportAgent as OperatorIcon,
  AccountCircle as UserIcon,
  Mail as EmailIcon,
  Key as KeyIcon,
  CheckCircle as ActiveIcon,
  Cancel as InactiveIcon,
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import api from '@/lib/api';

interface UserDetail {
  id: number;
  telegram_user_id: number;
  alias: string;
  full_name: string | null;
  email: string | null;
  role: string;
  is_active: boolean;
  kyc_status: string;
  balance_usdt: string;
  total_orders: number;
  created_at: string;
  sponsor_id: number | null;
  sponsor_alias: string | null;
}

export default function UserDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<UserDetail | null>(null);

  const [resetOpen, setResetOpen] = useState(false);
  const [tempPass, setTempPass] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '' });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<UserDetail>(`/users/${id}`);
      setUser(res.data);
    } catch (e: any) {
      setError(e.message || 'Error cargando usuario');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (token && id) load();
  }, [token, id, load]);

  const handleResetPassword = async () => {
    try {
      const res = await api.post<{ password_temp: string }>(`/users/${id}/reset-password`);
      setTempPass(res.data.password_temp);
      setResetOpen(true);
    } catch (e: any) {
      alert('Error en reset: ' + e.message);
    }
  };

  const handleCopy = () => {
    if (tempPass) {
      navigator.clipboard.writeText(tempPass);
      setSnackbar({ open: true, message: 'Password copiado al portapapeles' });
    }
  };

  const handleToggleActive = async () => {
    try {
      await api.put(`/users/${id}/toggle`);
      load();
    } catch (e: any) {
      alert('Error: ' + e.message);
    }
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}><CircularProgress /></Box>;
  if (!user) return <Box sx={{ p: 4 }}><Alert severity="error">Usuario no encontrado</Alert></Box>;

  return (
    <Box sx={{ p: 4 }}>
      <Button startIcon={<BackIcon />} onClick={() => router.back()} sx={{ mb: 4 }}>
        Volver a lista
      </Button>

      <Grid container spacing={4}>
        {/* Profile Card */}
        <Grid size={{ xs: 12, md: 4 }}>
          <Card elevation={0} sx={{ border: '1px solid #E2E8F0', borderRadius: 4, height: '100%' }}>
            <CardContent sx={{ p: 4, textAlign: 'center' }}>
              <Avatar sx={{ width: 100, height: 100, mx: 'auto', mb: 2, bgcolor: user.role === 'admin' ? '#FECACA' : '#E0E7FF', color: user.role === 'admin' ? '#B91C1C' : '#3730A3' }}>
                <UserIcon sx={{ fontSize: 60 }} />
              </Avatar>
              <Typography variant="h5" sx={{ fontWeight: 800 }}>{user.alias}</Typography>
              <Typography color="text.secondary" gutterBottom>{user.full_name || 'Sin nombre real'}</Typography>
              
              <Stack direction="row" spacing={1} justifyContent="center" sx={{ mt: 2, mb: 3 }}>
                <Chip 
                  icon={user.role === 'admin' ? <AdminIcon /> : <OperatorIcon />}
                  label={user.role.toUpperCase()} 
                  color={user.role === 'admin' ? 'error' : 'primary'}
                  size="small"
                  sx={{ fontWeight: 700 }}
                />
                <Chip 
                  label={user.is_active ? 'ACTIVO' : 'INACTIVO'} 
                  variant="outlined"
                  color={user.is_active ? 'success' : 'default'}
                  size="small"
                  sx={{ fontWeight: 700 }}
                />
              </Stack>

              <Divider sx={{ my: 3 }} />

              <Stack spacing={2}>
                <Button 
                  fullWidth variant="contained" color="secondary" 
                  startIcon={<ResetIcon />} sx={{ fontWeight: 700 }}
                  onClick={handleResetPassword}
                >
                  Reset Password
                </Button>
                <Button 
                  fullWidth variant="outlined" 
                  color={user.is_active ? 'error' : 'success'}
                  startIcon={user.is_active ? <InactiveIcon /> : <ActiveIcon />}
                  onClick={handleToggleActive}
                >
                  {user.is_active ? 'Desactivar Cuenta' : 'Activar Cuenta'}
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        {/* Data Cards */}
        <Grid size={{ xs: 12, md: 8 }}>
          <Stack spacing={4}>
            <Card elevation={0} sx={{ border: '1px solid #E2E8F0', borderRadius: 4 }}>
              <CardContent sx={{ p: 4 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>Información de Cuenta</Typography>
                <Grid container spacing={3}>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Telegram ID</Typography>
                    <Typography sx={{ fontWeight: 600 }}>{user.telegram_user_id}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Email</Typography>
                    <Typography sx={{ fontWeight: 600 }}>{user.email || 'No configurado'}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">KYC Status</Typography>
                    <Typography sx={{ fontWeight: 600 }}>{user.kyc_status}</Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="caption" color="text.secondary">Fecha Registro</Typography>
                    <Typography sx={{ fontWeight: 600 }}>{new Date(user.created_at).toLocaleDateString()}</Typography>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>

            <Card elevation={0} sx={{ border: '1px solid #E2E8F0', borderRadius: 4, bgcolor: '#F8FAFC' }}>
              <CardContent sx={{ p: 4 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 3 }}>Estadísticas Operativas</Typography>
                <Grid container spacing={4}>
                  <Grid item xs={12} sm={6}>
                    <Paper elevation={0} sx={{ p: 2, borderRadius: 3, border: '1px solid #E2E8F0' }}>
                      <Typography variant="caption" color="text.secondary">Balance Actual</Typography>
                      <Typography variant="h4" sx={{ fontWeight: 800, color: '#10B981' }}>
                        ${parseFloat(user.balance_usdt).toFixed(2)}
                      </Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Paper elevation={0} sx={{ p: 2, borderRadius: 3, border: '1px solid #E2E8F0' }}>
                      <Typography variant="caption" color="text.secondary">Órdenes Procesadas</Typography>
                      <Typography variant="h4" sx={{ fontWeight: 800 }}>
                        {user.total_orders}
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </Stack>
        </Grid>
      </Grid>

      {/* Reset Dialog */}
      <Dialog open={resetOpen} onClose={() => setResetOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle sx={{ fontWeight: 700 }}>Password Temporal Generado</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            Este password solo se mostrará <b>UNA VEZ</b>. Cópialo y envíaselo al usuario.
          </Alert>
          <Box sx={{
            p: 2, bgcolor: '#F1F5F9', borderRadius: 2,
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            border: '1px solid #E2E8F0'
          }}>
            <Typography sx={{ fontWeight: 800, fontFamily: 'monospace', fontSize: '1.2rem', color: '#1E293B' }}>
              {tempPass}
            </Typography>
            <IconButton onClick={handleCopy} color="primary" size="small">
              <CopyIcon />
            </IconButton>
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setResetOpen(false)} variant="contained" fullWidth>
            Entendido, ya lo copié
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}