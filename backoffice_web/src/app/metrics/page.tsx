'use client';

import React, { useState, useEffect, useCallback } from 'react';
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
  Tooltip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Divider,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  TrendingUp as ProfitIcon,
  Receipt as OrderIcon,
  AttachMoney as MoneyIcon,
  ShowChart as ChartIcon,
} from '@mui/icons-material';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  ResponsiveContainer,
} from 'recharts';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

/* ============ Types ============ */
interface MetricsOverview {
  total_orders: number;
  pending_orders: number;
  completed_orders: number;
  total_volume_usd: number;
  total_volume_dest: number;
  daily_volume: { date: string; volume: number }[];
}

interface CorridorMetric {
  route: string;
  volume: number;
  count: number;
  avg_rate: number;
}

interface P2PPrice {
  bank_name: string;
  amount: number;
  is_verified: boolean;
  captured_at: string;
}

export default function MetricsPage() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overview, setOverview] = useState<MetricsOverview | null>(null);
  const [corridors, setCorridors] = useState<CorridorMetric[]>([]);
  const [p2p, setP2P] = useState<P2PPrice[]>([]);

  const loadMetrics = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiRequest<{ overview: MetricsOverview; corridors: CorridorMetric[]; p2p: P2PPrice[] }>('/admin/metrics');
      setOverview(data.overview);
      setCorridors(data.corridors);
      setP2P(data.p2p);
    } catch (e: any) {
      console.error('Error metrics:', e);
      setError(e.message || 'No se pudieron cargar las métricas');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadMetrics();
  }, [loadMetrics]);

  const formatUsd = (val: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: '#1E293B' }}>Dashboard Metricas 10x</Typography>
          <Typography variant="body2" color="text.secondary">Visualización en tiempo real de volumen y operaciones</Typography>
        </Box>
        <Tooltip title="Recargar métricas">
          <IconButton onClick={loadMetrics}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Stack>

      {error ? (
        <Alert severity="error" sx={{ mb: 4 }}>{error}</Alert>
      ) : (
        <>
          {/* Summary Cards */}
          <Grid container spacing={3} sx={{ mb: 4 }}>
            {[
              { label: 'Volumen Total', value: formatUsd(overview?.total_volume_usd || 0), icon: <MoneyIcon sx={{ color: '#0052FF' }} />, color: '#0052FF15' },
              { label: 'Órdenes Totales', value: overview?.total_orders || 0, icon: <OrderIcon sx={{ color: '#10B981' }} />, color: '#10B98115' },
              { label: 'Órdenes Pendientes', value: overview?.pending_orders || 0, icon: <ChartIcon sx={{ color: '#F59E0B' }} />, color: '#F59E0B15' },
              { label: 'Crecimiento', value: '+12.5%', icon: <ProfitIcon sx={{ color: '#8B5CF6' }} />, color: '#8B5CF615' },
            ].map((card, idx) => (
              <Grid item xs={12} sm={6} md={3} key={idx}>
                <Card sx={{ borderRadius: 4, boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
                  <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Box sx={{ p: 1.5, borderRadius: 3, backgroundColor: card.color }}>{card.icon}</Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>{card.label}</Typography>
                      <Typography variant="h5" sx={{ fontWeight: 800 }}>{card.value}</Typography>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          {/* Charts Row */}
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <Grid item xs={12} md={8}>
              <Card sx={{ borderRadius: 4, height: '400px' }}>
                <CardContent sx={{ height: '100%' }}>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 1 }}>Volumen Diario (Last 30 Days)</Typography>
                  <ResponsiveContainer width="100%" height="85%">
                    <AreaChart data={overview?.daily_volume || []}>
                      <defs>
                        <linearGradient id="colorVol" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#0052FF" stopOpacity={0.1}/>
                          <stop offset="95%" stopColor="#0052FF" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
                      <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748B' }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748B' }} />
                      <ChartTooltip />
                      <Area type="monotone" dataKey="volume" stroke="#0052FF" fillOpacity={1} fill="url(#colorVol)" strokeWidth={3} />
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} md={4}>
              <Card sx={{ borderRadius: 4, height: '400px' }}>
                <CardContent>
                  <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Top Corredores</Typography>
                  <Stack spacing={2.5}>
                    {corridors.slice(0, 5).map((c, i) => (
                      <Box key={i}>
                        <Stack direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>{c.route}</Typography>
                          <Typography variant="caption" sx={{ color: '#0052FF', fontWeight: 700 }}>{formatUsd(c.volume)}</Typography>
                        </Stack>
                        <Box sx={{ width: '100%', height: 6, backgroundColor: '#F1F5F9', borderRadius: 3, overflow: 'hidden' }}>
                          <Box sx={{ width: `${Math.min(100, (c.volume / (overview?.total_volume_usd || 1)) * 100)}%`, height: '100%', backgroundColor: '#0052FF' }} />
                        </Box>
                      </Box>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* P2P Reality Table */}
          <Card sx={{ borderRadius: 4 }}>
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Monitoreo Binance P2P (VE)</Typography>
              {p2p.length > 0 ? (
                <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid #E2E8F0', borderRadius: 3 }}>
                  <Table>
                    <TableHead sx={{ backgroundColor: '#F8FAFC' }}>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 700 }}>Banco / Método</TableCell>
                        <TableCell sx={{ fontWeight: 700 }} align="right">Precio (Bs/$)</TableCell>
                        <TableCell sx={{ fontWeight: 700 }} align="center">Verificado</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Última Captura</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {p2p.map((p, i) => (
                        <TableRow key={i} hover>
                          <TableCell sx={{ fontWeight: 600 }}>{p.bank_name}</TableCell>
                          <TableCell align="right" sx={{ color: '#16A34A', fontWeight: 800 }}>{p.amount.toFixed(2)}</TableCell>
                          <TableCell align="center">{p.is_verified ? <Chip label="Si" size="small" sx={{ backgroundColor: '#16A34A15', color: '#16A34A', fontWeight: 700, height: 20 }} /> : <Chip label="No" size="small" sx={{ height: 20 }} />}</TableCell>
                          <TableCell sx={{ fontSize: '0.75rem', color: '#64748B' }}>
                            {p.captured_at ? new Date(p.captured_at).toLocaleString('es-VE', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '-'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Box sx={{ py: 6, textAlign: 'center' }}><Typography variant="body2" color="text.secondary">Sin datos de precios P2P</Typography></Box>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  );
}
