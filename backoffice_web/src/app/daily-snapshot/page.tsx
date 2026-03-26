'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Card, CardContent, Stack, TextField,
  Alert, CircularProgress, Divider, IconButton, Tooltip,
  Grid
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Receipt as OrderIcon,
  AttachMoney as MoneyIcon,
  AccountBalance as VaultIcon,
  Payments as PayoutIcon,
  NotificationsActive as RequestIcon,
  TrendingUp as ProfitIcon,
  Info as InfoIcon
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

interface DailySnapshot {
  date: string;
  orders_completed: number;
  volume_usd: number;
  gross_profit_today: number;
  commissions_today: number;
  net_retained_today: number;
  payouts_today: number;
  new_withdrawal_requests: number;
  disclaimer: string;
}

const formatCurrency = (amount: number) => {
  return '$' + (amount || 0).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
};

interface StatCardProps {
  title: string;
  value: string | number;
  Icon: React.ElementType;
  color: string;
  subtitle?: string;
}

function StatCard({ title, value, Icon, color, subtitle }: StatCardProps) {
  return (
    <Card sx={{ height: '100%', minWidth: 200 }}>
      <CardContent sx={{ p: 2.5 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography variant="body2" sx={{ color: '#64748B', fontSize: '0.8rem', mb: 0.5, fontWeight: 500 }}>{title}</Typography>
            <Typography variant="h4" sx={{ fontWeight: 800, color: '#111827', lineHeight: 1.1 }}>{value}</Typography>
            {subtitle && <Typography variant="caption" sx={{ color: '#64748B', mt: 0.5, display: 'block' }}>{subtitle}</Typography>}
          </Box>
          <Box sx={{ backgroundColor: color + '12', borderRadius: '12px', p: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Icon sx={{ color, fontSize: 24 }} />
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

export default function DailySnapshotPage() {
  const { token, role } = useAuth();
  const [selectedDate, setSelectedDate] = useState('');
  const [snapshot, setSnapshot] = useState<DailySnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Inicializar con la fecha de ayer por defecto
  useEffect(() => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    setSelectedDate(yesterday.toISOString().split('T')[0]);
  }, []);

  const fetchData = useCallback(async (date: string) => {
    if (!date) return;
    setLoading(true);
    setError('');
    try {
      const data = await apiRequest<DailySnapshot>(`/admin/metrics/daily_snapshot?date=${date}`);
      setSnapshot(data);
    } catch (err: any) {
      setError(err.message || 'Error al obtener el snapshot diario');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token && selectedDate && role === 'admin') {
      fetchData(selectedDate);
    }
  }, [token, selectedDate, role, fetchData]);

  if (role !== 'admin') {
    return <Alert severity="error">Acceso restringido a administradores.</Alert>;
  }

  return (
    <Box className="fade-in">
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: '#111827' }}>Snapshot Diario</Typography>
          <Typography variant="body2" sx={{ color: '#64748B', mt: 0.5 }}>Resumen financiero ejecutivo de un día específico</Typography>
        </Box>
        <Stack direction="row" spacing={2} alignItems="center">
          <TextField
            type="date"
            size="small"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            sx={{
               width: 180,
               '& .MuiInputBase-root': { borderRadius: '10px', backgroundColor: '#fff' }
            }}
          />
          <Tooltip title="Actualizar">
            <IconButton 
              onClick={() => fetchData(selectedDate)} 
              disabled={loading}
              sx={{ color: '#4B2E83', border: '1px solid #E9E3F7', borderRadius: '10px', p: 1 }}
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 3, borderRadius: '12px' }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 12 }}>
          <CircularProgress sx={{ color: '#4B2E83' }} />
        </Box>
      ) : (
        snapshot && (
          <>
            <Grid container spacing={3} sx={{ mb: 4 }}>
              <Grid item xs={12} md={4}>
                <StatCard 
                  title="Órdenes Completadas" 
                  value={snapshot.orders_completed} 
                  Icon={OrderIcon} 
                  color="#4B2E83" 
                  subtitle="Registros internos"
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <StatCard 
                  title="Volumen USD/USDT" 
                  value={formatCurrency(snapshot.volume_usd)} 
                  Icon={MoneyIcon} 
                  color="#16A34A" 
                  subtitle="Filtrado por moneda base"
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <StatCard 
                  title="Utilidad Real del Día" 
                  value={formatCurrency(snapshot.gross_profit_today)} 
                  Icon={ProfitIcon} 
                  color="#2563EB" 
                  subtitle="Profit real total"
                />
              </Grid>
            </Grid>

            <Card sx={{ mb: 4, borderRadius: '16px', overflow: 'hidden', border: '1px solid #E9E3F7' }}>
              <CardContent sx={{ p: 0 }}>
                <Box sx={{ p: 3, background: 'linear-gradient(135deg, #1E3A5F 0%, #2563EB 100%)', color: '#fff' }}>
                   <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                    <VaultIcon sx={{ fontSize: 20, opacity: 0.8 }} />
                    <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      Utilidad Retenida del Día
                    </Typography>
                  </Stack>
                  <Typography variant="h3" sx={{ fontWeight: 900, letterSpacing: '-0.02em' }}>
                    {formatCurrency(snapshot.net_retained_today)}
                  </Typography>
                  <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.6)', mt: 1, fontSize: '0.85rem' }}>
                    {formatCurrency(snapshot.gross_profit_today)} utilidad bruta − {formatCurrency(snapshot.commissions_today)} comisiones
                  </Typography>
                </Box>
                <Divider />
                <Box sx={{ p: 3, backgroundColor: '#FAF8FF' }}>
                  <Grid container spacing={4}>
                    <Grid item xs={12} md={6}>
                      <Stack spacing={2}>
                        <Box>
                          <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600 }}>Comisiones Operadores</Typography>
                          <Typography variant="h6" sx={{ fontWeight: 700, color: '#111827' }}>
                            {formatCurrency(snapshot.commissions_today)}
                          </Typography>
                        </Box>
                        <Box>
                          <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600 }}>Nuevas Solicitudes de Retiro</Typography>
                          <Stack direction="row" alignItems="center" spacing={1}>
                            <Typography variant="h6" sx={{ fontWeight: 700, color: snapshot.new_withdrawal_requests > 0 ? '#DC2626' : '#111827' }}>
                              {snapshot.new_withdrawal_requests}
                            </Typography>
                            {snapshot.new_withdrawal_requests > 0 && <RequestIcon sx={{ color: '#DC2626', fontSize: 18 }} />}
                          </Stack>
                        </Box>
                      </Stack>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Stack spacing={2}>
                        <Box>
                          <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600 }}>Retiros Pagados Hoy</Typography>
                          <Stack direction="row" alignItems="center" spacing={1}>
                            <Typography variant="h6" sx={{ fontWeight: 700, color: '#16A34A' }}>
                              {formatCurrency(snapshot.payouts_today)}
                            </Typography>
                            <PayoutIcon sx={{ color: '#16A34A', fontSize: 18 }} />
                          </Stack>
                        </Box>
                        <Box sx={{ display: 'flex', alignItems: 'flex-start', pt: 1 }}>
                           <InfoIcon sx={{ fontSize: 16, color: '#64748B', mr: 1, mt: 0.2 }} />
                           <Typography variant="caption" sx={{ color: '#64748B', fontStyle: 'italic', maxWidth: 400 }}>
                             Recuerda que los retiros pagados reflejan salidas ejecutadas, mientras que la utilidad retenida es un valor devengado.
                           </Typography>
                        </Box>
                      </Stack>
                    </Grid>
                  </Grid>
                </Box>
              </CardContent>
            </Card>

            <Box sx={{ mt: 4, mb: 2 }}>
               <Alert 
                 severity="info" 
                 icon={false}
                 sx={{ 
                   backgroundColor: 'transparent', 
                   border: '1px dashed #D8CCFF',
                   '& .MuiAlert-message': { color: '#64748B', fontSize: '0.75rem', textAlign: 'center', width: '100%' } 
                 }}
               >
                 {snapshot.disclaimer}
               </Alert>
            </Box>
          </>
        )
      )}
    </Box>
  );
}
