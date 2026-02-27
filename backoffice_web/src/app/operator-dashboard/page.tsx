'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Card, CardContent, CircularProgress,
  Chip, Stack, Divider, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Paper, Alert,
  Avatar, LinearProgress,
} from '@mui/material';
import {
  AccountBalanceWallet as WalletIcon,
  TrendingUp as ProfitIcon,
  Receipt as OrderIcon,
  People as ReferralIcon,
  ArrowUpward as WithdrawIcon,
  PaymentsOutlined as PaidIcon,
} from '@mui/icons-material';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

/* ═══════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════ */

interface WalletData {
  balance_usdt: string;
  profit_today: string;
  profit_month: string;
  profit_total: string;
  referrals_month: string;
}

interface ProfitByCountry {
  origin_country: string;
  total_profit_usdt: string;
  order_count: number;
}

interface Order {
  public_id: string;
  origin_country: string;
  dest_country: string;
  amount_origin: string;
  payout_dest: string;
  profit_usdt: string;
  status: string;
  created_at: string;
}

interface Withdrawal {
  id: number;
  amount_usdt: string;
  status: string;
  dest_text: string;
  country: string;
  created_at: string;
  resolved_at: string | null;
}

interface DashboardData {
  ok: boolean;
  user: { alias: string; full_name: string; role: string };
  wallet: WalletData;
  profit_by_country: ProfitByCountry[];
  recent_orders: Order[];
  withdrawals: Withdrawal[];
  referrals_count: number;
}

/* ═══════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════ */

const fmt = (val: string | number, prefix = '$') =>
  `${prefix}${Number(val).toFixed(2)}`;

const fmtDate = (iso: string) =>
  iso ? new Date(iso).toLocaleString('es-VE', {
    day: '2-digit', month: '2-digit', year: '2-digit',
    hour: '2-digit', minute: '2-digit',
  }) : '-';

const STATUS_COLORS: Record<string, 'success' | 'warning' | 'error' | 'default' | 'info'> = {
  PAGADA: 'success',
  EN_PROCESO: 'info',
  ORIGEN_VERIFICANDO: 'warning',
  ORIGEN_CONFIRMADO: 'warning',
  CREADA: 'default',
  CANCELADA: 'error',
};

const STATUS_LABELS: Record<string, string> = {
  PAGADA: 'Pagada',
  EN_PROCESO: 'En proceso',
  ORIGEN_VERIFICANDO: 'Verificando',
  ORIGEN_CONFIRMADO: 'Confirmado',
  CREADA: 'Creada',
  CANCELADA: 'Cancelada',
  APROBADO: 'Aprobado',
  PENDIENTE: 'Pendiente',
  RECHAZADO: 'Rechazado',
};

const COUNTRY_FLAGS: Record<string, string> = {
  USA: '🇺🇸', CHILE: '🇨🇱', COLOMBIA: '🇨🇴', PERU: '🇵🇪',
  VENEZUELA: '🇻🇪', MEXICO: '🇲🇽', ECUADOR: '🇪🇨',
  ARGENTINA: '🇦🇷', PANAMA: '🇵🇦',
};

const CHART_COLORS = ['#6C63FF', '#FF6584', '#43AA8B', '#F9C74F', '#90E0EF', '#FF9F1C'];

/* ═══════════════════════════════════════════════════
   KPI Card Component
   ═══════════════════════════════════════════════════ */

function KpiCard({
  label, value, sub, icon, color, gradient,
}: {
  label: string; value: string; sub?: string;
  icon: React.ReactNode; color: string; gradient: string;
}) {
  return (
    <Card sx={{
      flex: 1, minWidth: 0, borderRadius: 3,
      background: gradient,
      boxShadow: '0 4px 20px rgba(0,0,0,0.18)',
      position: 'relative', overflow: 'hidden',
    }}>
      <CardContent sx={{ p: 2.5 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" mb={1}>
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.8)', fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase' }}>
            {label}
          </Typography>
          <Avatar sx={{ bgcolor: 'rgba(255,255,255,0.15)', width: 36, height: 36 }}>
            {icon}
          </Avatar>
        </Stack>
        <Typography variant="h5" sx={{ color: '#fff', fontWeight: 800, fontFamily: 'monospace' }}>
          {value}
        </Typography>
        {sub && (
          <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.7)' }}>
            {sub}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
}

/* ═══════════════════════════════════════════════════
   Main Page
   ═══════════════════════════════════════════════════ */

export default function OperatorDashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiRequest('/operator/me/dashboard');
      setData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error al cargar el dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <Box display="flex" justifyContent="center" alignItems="center" minHeight="80vh" flexDirection="column" gap={2}>
      <CircularProgress size={48} sx={{ color: '#6C63FF' }} />
      <Typography sx={{ color: '#aaa' }}>Cargando tu dashboard…</Typography>
    </Box>
  );

  if (error) return (
    <Box p={4}><Alert severity="error">{error}</Alert></Box>
  );

  if (!data) return null;

  const { wallet, profit_by_country, recent_orders, withdrawals, referrals_count, user: u } = data;

  const chartData = profit_by_country.map(p => ({
    country: `${COUNTRY_FLAGS[p.origin_country] || '🌍'} ${p.origin_country}`,
    profit: Number(p.total_profit_usdt),
    orders: p.order_count,
  }));

  return (
    <Box sx={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0f0c29, #302b63, #24243e)',
      p: { xs: 2, md: 4 },
    }}>
      {/* Header */}
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={4}>
        <Box>
          <Typography variant="h4" sx={{
            color: '#fff', fontWeight: 800,
            background: 'linear-gradient(90deg, #6C63FF, #FF6584)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>
            Mi Dashboard
          </Typography>
          <Typography sx={{ color: 'rgba(255,255,255,0.5)', mt: 0.5 }}>
            Bienvenido, <b style={{ color: '#fff' }}>{u?.full_name || u?.alias}</b> · Operador Sendmax
          </Typography>
        </Box>
        <Chip
          label={`${referrals_count} referido${referrals_count !== 1 ? 's' : ''}`}
          icon={<ReferralIcon />}
          sx={{ color: '#fff', borderColor: 'rgba(255,255,255,0.3)', bgcolor: 'rgba(255,255,255,0.08)' }}
          variant="outlined"
          size="small"
        />
      </Stack>

      {/* KPI Row */}
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} mb={4}>
        <KpiCard
          label="Saldo Disponible"
          value={fmt(wallet.balance_usdt)}
          sub="USDT en billetera"
          icon={<WalletIcon sx={{ color: '#fff', fontSize: 20 }} />}
          color="#6C63FF"
          gradient="linear-gradient(135deg, #6C63FF 0%, #9B59B6 100%)"
        />
        <KpiCard
          label="Ganancia Hoy"
          value={fmt(wallet.profit_today)}
          sub="USDT en profit"
          icon={<ProfitIcon sx={{ color: '#fff', fontSize: 20 }} />}
          color="#43AA8B"
          gradient="linear-gradient(135deg, #43AA8B 0%, #52b788 100%)"
        />
        <KpiCard
          label="Ganancia Este Mes"
          value={fmt(wallet.profit_month)}
          sub="USD acumulado"
          icon={<OrderIcon sx={{ color: '#fff', fontSize: 20 }} />}
          color="#FF6584"
          gradient="linear-gradient(135deg, #FF6584 0%, #ee4540 100%)"
        />
        <KpiCard
          label="Comisiones Mes"
          value={fmt(wallet.referrals_month)}
          sub="De referidos"
          icon={<PaidIcon sx={{ color: '#fff', fontSize: 20 }} />}
          color="#F9C74F"
          gradient="linear-gradient(135deg, #F9C74F 0%, #f4a261 100%)"
        />
      </Stack>

      {/* Chart + Orders */}
      <Stack direction={{ xs: 'column', lg: 'row' }} spacing={3} mb={4}>
        {/* Bar Chart */}
        <Card sx={{ flex: 1, background: 'rgba(255,255,255,0.05)', borderRadius: 3, border: '1px solid rgba(255,255,255,0.1)' }}>
          <CardContent>
            <Typography variant="h6" sx={{ color: '#fff', fontWeight: 700, mb: 2 }}>
              💰 Ganancias por País de Origen
            </Typography>
            {chartData.length === 0 ? (
              <Typography sx={{ color: '#aaa', textAlign: 'center', py: 4 }}>Sin datos aún</Typography>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                  <XAxis dataKey="country" tick={{ fill: '#ccc', fontSize: 11 }} />
                  <YAxis tick={{ fill: '#ccc', fontSize: 11 }} />
                  <RechartsTooltip
                    contentStyle={{ background: '#1a1a2e', border: 'none', borderRadius: 8, color: '#fff' }}
                    formatter={(v: number) => [`$${v.toFixed(2)} USDT`, 'Ganancia']}
                  />
                  <Bar dataKey="profit" radius={[6, 6, 0, 0]}>
                    {chartData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Recent Orders */}
        <Card sx={{ flex: 1.2, background: 'rgba(255,255,255,0.05)', borderRadius: 3, border: '1px solid rgba(255,255,255,0.1)' }}>
          <CardContent sx={{ p: 0 }}>
            <Typography variant="h6" sx={{ color: '#fff', fontWeight: 700, p: 2.5, pb: 1 }}>
              📋 Últimas Órdenes
            </Typography>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    {['ID', 'Ruta', 'Enviado', 'Profit', 'Estado', 'Fecha'].map(h => (
                      <TableCell key={h} sx={{ color: 'rgba(255,255,255,0.5)', borderColor: 'rgba(255,255,255,0.08)', fontSize: 11, py: 1 }}>
                        {h}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(recent_orders || []).slice(0, 10).map(o => (
                    <TableRow key={o.public_id} hover sx={{ '&:hover': { background: 'rgba(255,255,255,0.04)' } }}>
                      <TableCell sx={{ color: '#a78bfa', borderColor: 'rgba(255,255,255,0.05)', fontSize: 11, fontFamily: 'monospace' }}>
                        {o.public_id}
                      </TableCell>
                      <TableCell sx={{ color: '#fff', borderColor: 'rgba(255,255,255,0.05)', fontSize: 11 }}>
                        {COUNTRY_FLAGS[o.origin_country] || '🌍'}→{COUNTRY_FLAGS[o.dest_country] || '🌍'}
                      </TableCell>
                      <TableCell sx={{ color: '#ccc', borderColor: 'rgba(255,255,255,0.05)', fontSize: 11 }}>
                        {Number(o.amount_origin).toFixed(2)}
                      </TableCell>
                      <TableCell sx={{ color: '#43AA8B', borderColor: 'rgba(255,255,255,0.05)', fontSize: 11, fontWeight: 700 }}>
                        {o.profit_usdt ? `$${Number(o.profit_usdt).toFixed(2)}` : '-'}
                      </TableCell>
                      <TableCell sx={{ borderColor: 'rgba(255,255,255,0.05)' }}>
                        <Chip
                          label={STATUS_LABELS[o.status] || o.status}
                          color={STATUS_COLORS[o.status] || 'default'}
                          size="small"
                          sx={{ fontSize: 10, height: 20 }}
                        />
                      </TableCell>
                      <TableCell sx={{ color: '#888', borderColor: 'rgba(255,255,255,0.05)', fontSize: 10 }}>
                        {fmtDate(o.created_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                  {(!recent_orders || recent_orders.length === 0) && (
                    <TableRow>
                      <TableCell colSpan={6} sx={{ textAlign: 'center', color: '#666', py: 4, borderColor: 'rgba(255,255,255,0.05)' }}>
                        Sin órdenes aún
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Stack>

      {/* Withdrawals */}
      <Card sx={{ background: 'rgba(255,255,255,0.05)', borderRadius: 3, border: '1px solid rgba(255,255,255,0.1)' }}>
        <CardContent sx={{ p: 0 }}>
          <Stack direction="row" alignItems="center" gap={1} sx={{ p: 2.5, pb: 1 }}>
            <WithdrawIcon sx={{ color: '#F9C74F' }} />
            <Typography variant="h6" sx={{ color: '#fff', fontWeight: 700 }}>
              Historial de Retiros
            </Typography>
          </Stack>
          <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)' }} />
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  {['Monto', 'Destino', 'País', 'Estado', 'Solicitado', 'Resuelto'].map(h => (
                    <TableCell key={h} sx={{ color: 'rgba(255,255,255,0.5)', borderColor: 'rgba(255,255,255,0.08)', fontSize: 11, py: 1 }}>
                      {h}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {(withdrawals || []).map(w => (
                  <TableRow key={w.id} hover sx={{ '&:hover': { background: 'rgba(255,255,255,0.04)' } }}>
                    <TableCell sx={{ color: '#F9C74F', borderColor: 'rgba(255,255,255,0.05)', fontSize: 13, fontWeight: 700 }}>
                      ${Number(w.amount_usdt).toFixed(2)}
                    </TableCell>
                    <TableCell sx={{ color: '#ccc', borderColor: 'rgba(255,255,255,0.05)', fontSize: 12 }}>
                      {w.dest_text || '-'}
                    </TableCell>
                    <TableCell sx={{ color: '#ccc', borderColor: 'rgba(255,255,255,0.05)', fontSize: 12 }}>
                      {COUNTRY_FLAGS[w.country] || ''} {w.country}
                    </TableCell>
                    <TableCell sx={{ borderColor: 'rgba(255,255,255,0.05)' }}>
                      <Chip
                        label={STATUS_LABELS[w.status] || w.status}
                        color={w.status === 'APROBADO' ? 'success' : w.status === 'RECHAZADO' ? 'error' : 'warning'}
                        size="small"
                        sx={{ fontSize: 10, height: 20 }}
                      />
                    </TableCell>
                    <TableCell sx={{ color: '#888', borderColor: 'rgba(255,255,255,0.05)', fontSize: 11 }}>
                      {fmtDate(w.created_at)}
                    </TableCell>
                    <TableCell sx={{ color: w.resolved_at ? '#43AA8B' : '#555', borderColor: 'rgba(255,255,255,0.05)', fontSize: 11 }}>
                      {w.resolved_at ? fmtDate(w.resolved_at) : '—'}
                    </TableCell>
                  </TableRow>
                ))}
                {(!withdrawals || withdrawals.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={6} sx={{ textAlign: 'center', color: '#666', py: 4, borderColor: 'rgba(255,255,255,0.05)' }}>
                      Sin retiros registrados
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Total Profit Footer */}
      <Box sx={{ mt: 3, p: 2.5, background: 'rgba(108,99,255,0.12)', borderRadius: 3, border: '1px solid rgba(108,99,255,0.3)', textAlign: 'center' }}>
        <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.5)', display: 'block', mb: 0.5 }}>
          Ganancia acumulada total (histórico)
        </Typography>
        <Typography variant="h5" sx={{ color: '#6C63FF', fontWeight: 800, fontFamily: 'monospace' }}>
          {fmt(wallet.profit_total)} USDT
        </Typography>
      </Box>
    </Box>
  );
}
