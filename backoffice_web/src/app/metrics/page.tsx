'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Stack,
  Button,
  Alert,
  CircularProgress,
  Chip,
  Divider,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  TrendingUp as ProfitIcon,
  Receipt as OrderIcon,
  AttachMoney as MoneyIcon,
  ShowChart as ChartIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  PieChart,
  Pie,
} from 'recharts';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

interface MetricsOverview {
  total_orders: number;
  pending_orders: number;
  completed_orders: number;
  total_profit_usd: number;
  status_counts: Record<string, number>;
}

interface ProfitDayRaw {
  day: string;
  total_orders: number;
  total_profit: number;
  total_volume: number;
}

interface ProfitDailyResponse {
  days: number;
  profit_by_day: ProfitDayRaw[];
}

interface CompanyOverview {
  ok: boolean;
  orders: { total_orders: number; pending_orders: number; completed_orders: number };
  profit: { total_profit_usd: number };
  volume: {
    paid_usd_usdt: number;
    paid_by_dest_currency: { dest_currency: string; volume: number }[];
  };
  origin_wallets: {
    pending_total: number;
    top_pending: { origin_country: string; fiat_currency: string; current_balance: number }[];
  };
}

interface OrderItem {
  public_id: number;
  status: string;
  profit_usdt: number;
  origin_country: string;
  dest_country: string;
  amount_origin: number;
  payout_dest: number;
  created_at: string;
}

interface OrdersResponse {
  count: number;
  orders: OrderItem[];
}

const COLORS = ['#4B2E83', '#6B46C1', '#2563EB', '#16A34A', '#F59E0B', '#DC2626', '#8B5CF6', '#06B6D4'];
const STATUS_COLORS: Record<string, string> = {
  PAGADA: '#16A34A', CANCELADA: '#DC2626', CREADA: '#F59E0B',
  EN_PROCESO: '#2563EB', ORIGEN_VERIFICANDO: '#8B5CF6', COMPLETADA: '#16A34A',
};

export default function MetricsPage() {
  const { apiKey } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [days, setDays] = useState(7);

  const [overview, setOverview] = useState<MetricsOverview | null>(null);
  const [company, setCompany] = useState<CompanyOverview | null>(null);
  const [profitDaily, setProfitDaily] = useState<{ day: string; profit: number; orders: number; volume: number }[]>([]);
  const [corridorData, setCorridorData] = useState<{ name: string; volume: number; count: number; profit: number }[]>([]);
  const [statusData, setStatusData] = useState<{ name: string; value: number; color: string }[]>([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [overviewData, companyData, profitData, ordersData] = await Promise.all([
        apiRequest<MetricsOverview>('/metrics/overview'),
        apiRequest<CompanyOverview>('/metrics/company-overview').catch(() => null),
        apiRequest<ProfitDailyResponse>(`/metrics/profit_daily?days=${days}`).catch(() => null),
        apiRequest<OrdersResponse>('/orders?limit=500').catch(() => ({ count: 0, orders: [] })),
      ]);

      setOverview(overviewData);
      setCompany(companyData);

      if (profitData?.profit_by_day) {
        setProfitDaily(profitData.profit_by_day.map((d) => ({
          day: new Date(d.day).toLocaleDateString('es-VE', { weekday: 'short', day: 'numeric', month: 'short' }),
          profit: d.total_profit,
          orders: d.total_orders,
          volume: d.total_volume,
        })));
      }

      const ordersArray = Array.isArray(ordersData) ? ordersData : (ordersData.orders || []);

      // Corridors
      const corridors: Record<string, { volume: number; count: number; profit: number }> = {};
      ordersArray.forEach((o: OrderItem) => {
        const key = `${o.origin_country} → ${o.dest_country}`;
        if (!corridors[key]) corridors[key] = { volume: 0, count: 0, profit: 0 };
        corridors[key].volume += o.amount_origin || 0;
        corridors[key].count += 1;
        corridors[key].profit += o.profit_usdt || 0;
      });
      setCorridorData(Object.entries(corridors).map(([name, data]) => ({ name, ...data })).sort((a, b) => b.profit - a.profit));

      // Status from API
      if (overviewData?.status_counts) {
        setStatusData(Object.entries(overviewData.status_counts).filter(([, v]) => v > 0).map(([name, value]) => ({
          name, value, color: STATUS_COLORS[name] || '#6B7280',
        })));
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { if (apiKey) fetchData(); }, [apiKey, fetchData]);

  const totalProfit = overview?.total_profit_usd || 0;
  const totalOrders = overview?.total_orders || 0;
  const avgProfit = totalOrders > 0 ? totalProfit / totalOrders : 0;
  const completed = overview?.completed_orders || 0;
  const convRate = totalOrders > 0 ? ((completed / totalOrders) * 100) : 0;

  const exportCSV = () => {
    if (corridorData.length === 0) return;
    const headers = ['Corredor', 'Volumen', 'Ordenes', 'Profit USDT'];
    const rows = corridorData.map((c) => [c.name, c.volume.toFixed(2), c.count, c.profit.toFixed(2)]);
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `metricas_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  return (
    <Box className="fade-in">
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>Metricas y Analisis</Typography>
          <Typography variant="body2" sx={{ color: '#64748B', mt: 0.5 }}>Rendimiento, corredores y rentabilidad</Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Periodo</InputLabel>
            <Select value={days} onChange={(e) => setDays(Number(e.target.value))} label="Periodo">
              <MenuItem value={7}>7 dias</MenuItem>
              <MenuItem value={14}>14 dias</MenuItem>
              <MenuItem value={30}>30 dias</MenuItem>
              <MenuItem value={90}>90 dias</MenuItem>
            </Select>
          </FormControl>
          <Button variant="outlined" startIcon={<DownloadIcon />} onClick={exportCSV} size="small">CSV</Button>
          <Button variant="contained" startIcon={<RefreshIcon />} onClick={fetchData} disabled={loading}>Actualizar</Button>
        </Stack>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress sx={{ color: '#4B2E83' }} /></Box>
      ) : (
        <>
          {/* KPIs */}
          <Stack direction="row" spacing={2.5} sx={{ mb: 4, flexWrap: 'wrap', gap: 2 }}>
            {[
              { title: 'Profit Total', value: `$${totalProfit.toFixed(2)}`, icon: <MoneyIcon sx={{ color: '#16A34A', fontSize: 26 }} />, bg: '#16A34A12', sub: 'USDT acumulado' },
              { title: 'Ordenes Totales', value: totalOrders, icon: <OrderIcon sx={{ color: '#4B2E83', fontSize: 26 }} />, bg: '#4B2E8312', sub: `${overview?.pending_orders || 0} pendientes` },
              { title: 'Profit Promedio', value: `$${avgProfit.toFixed(2)}`, icon: <ChartIcon sx={{ color: '#2563EB', fontSize: 26 }} />, bg: '#2563EB12', sub: 'Por orden' },
              { title: 'Tasa Conversion', value: `${convRate.toFixed(1)}%`, icon: <ProfitIcon sx={{ color: '#F59E0B', fontSize: 26 }} />, bg: '#F59E0B12', sub: `${completed} completadas` },
            ].map((c, i) => (
              <Card key={i} sx={{ flex: '1 1 calc(25% - 16px)', minWidth: 200 }}>
                <CardContent sx={{ p: 2.5 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                    <Box>
                      <Typography variant="body2" sx={{ color: '#64748B', fontSize: '0.8rem', mb: 0.5 }}>{c.title}</Typography>
                      <Typography variant="h4" sx={{ fontWeight: 700, color: '#111827' }}>{c.value}</Typography>
                      <Typography variant="caption" sx={{ color: '#64748B' }}>{c.sub}</Typography>
                    </Box>
                    <Box sx={{ backgroundColor: c.bg, borderRadius: '14px', p: 1.25 }}>{c.icon}</Box>
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Stack>

          {/* Charts */}
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2.5} sx={{ mb: 3 }}>
            <Card sx={{ flex: 2 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>Ganancia Diaria</Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>{`Ultimos ${days} dias`}</Typography>
                  </Box>
                  <Chip label={`${days}d`} size="small" sx={{ backgroundColor: '#EFEAFF', color: '#4B2E83', fontWeight: 700 }} />
                </Stack>
                {profitDaily.length > 0 ? (
                  <ResponsiveContainer width="100%" height={280}>
                    <AreaChart data={profitDaily}>
                      <defs>
                        <linearGradient id="profitGrad2" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#4B2E83" stopOpacity={0.3} />
                          <stop offset="100%" stopColor="#4B2E83" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E9E3F7" vertical={false} />
                      <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={{ stroke: '#E9E3F7' }} tickLine={false} />
                      <YAxis tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `$${v}`} />
                      <RechartsTooltip contentStyle={{ borderRadius: 12, border: '1px solid #E9E3F7', fontSize: 13 }} formatter={(v: unknown) => [`$${Number(v ?? 0).toFixed(2)}`, 'Ganancia']} />
                      <Area type="monotone" dataKey="profit" stroke="#4B2E83" strokeWidth={2.5} fill="url(#profitGrad2)" dot={{ fill: '#4B2E83', r: 4, strokeWidth: 2, stroke: '#FFF' }} />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <Box sx={{ py: 8, textAlign: 'center' }}><Typography variant="body2" color="text.secondary">Sin datos para este periodo</Typography></Box>
                )}
              </CardContent>
            </Card>

            <Card sx={{ flex: 1, minWidth: 300 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 0.5 }}>Por Status</Typography>
                <Typography variant="caption" sx={{ color: '#64748B', display: 'block', mb: 2 }}>Distribucion de ordenes</Typography>
                {statusData.length > 0 ? (
                  <>
                    <ResponsiveContainer width="100%" height={200}>
                      <PieChart>
                        <Pie data={statusData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} dataKey="value" stroke="none">
                          {statusData.map((e, i) => <Cell key={i} fill={e.color} />)}
                        </Pie>
                        <RechartsTooltip contentStyle={{ borderRadius: 12, fontSize: 13 }} />
                      </PieChart>
                    </ResponsiveContainer>
                    <Stack spacing={1} sx={{ mt: 1 }}>
                      {statusData.map((s) => (
                        <Stack key={s.name} direction="row" justifyContent="space-between" alignItems="center">
                          <Stack direction="row" spacing={1} alignItems="center">
                            <Box sx={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: s.color }} />
                            <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>{s.name}</Typography>
                          </Stack>
                          <Chip label={s.value} size="small" sx={{ backgroundColor: `${s.color}15`, color: s.color, fontWeight: 700, height: 22 }} />
                        </Stack>
                      ))}
                    </Stack>
                  </>
                ) : (
                  <Box sx={{ py: 6, textAlign: 'center' }}><Typography variant="body2" color="text.secondary">Sin datos</Typography></Box>
                )}
              </CardContent>
            </Card>
          </Stack>

          {/* Corridors */}
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 700 }}>Analisis por Corredor</Typography>
                  <Typography variant="caption" sx={{ color: '#64748B' }}>Rendimiento por ruta</Typography>
                </Box>
                <Chip label={`${corridorData.length} rutas`} size="small" sx={{ backgroundColor: '#EFEAFF', color: '#4B2E83', fontWeight: 700 }} />
              </Stack>
              <Divider sx={{ mb: 2 }} />
              {corridorData.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={Math.max(200, corridorData.length * 45)}>
                    <BarChart data={corridorData} layout="vertical" margin={{ left: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E9E3F7" horizontal={false} />
                      <XAxis type="number" tick={{ fontSize: 11, fill: '#64748B' }} tickFormatter={(v: number) => `$${v.toFixed(0)}`} />
                      <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} width={160} />
                      <RechartsTooltip contentStyle={{ borderRadius: 12, fontSize: 13 }} formatter={(v: unknown, n: string) => [`$${Number(v ?? 0).toFixed(2)}`, n === 'profit' ? 'Profit' : 'Volumen']} />
                      <Bar dataKey="profit" radius={[0, 6, 6, 0]} barSize={20}>
                        {corridorData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  <Divider sx={{ my: 2 }} />
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Corredor</TableCell>
                          <TableCell align="right">Ordenes</TableCell>
                          <TableCell align="right">Volumen</TableCell>
                          <TableCell align="right">Profit</TableCell>
                          <TableCell align="right">Avg Profit</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {corridorData.map((c, i) => (
                          <TableRow key={i} hover>
                            <TableCell sx={{ fontWeight: 600 }}>
                              <Stack direction="row" spacing={1} alignItems="center">
                                <Box sx={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: COLORS[i % COLORS.length] }} />
                                <Typography variant="body2">{c.name}</Typography>
                              </Stack>
                            </TableCell>
                            <TableCell align="right"><Chip label={c.count} size="small" sx={{ fontWeight: 700, height: 22 }} /></TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>{c.volume.toLocaleString('es-VE', { minimumFractionDigits: 2 })}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 700, color: '#16A34A' }}>{`$${c.profit.toFixed(2)}`}</TableCell>
                            <TableCell align="right" sx={{ color: '#64748B' }}>{`$${c.count > 0 ? (c.profit / c.count).toFixed(2) : '0.00'}`}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </>
              ) : (
                <Box sx={{ py: 6, textAlign: 'center' }}><Typography variant="body2" color="text.secondary">Sin datos</Typography></Box>
              )}
            </CardContent>
          </Card>

          {/* Volume by currency */}
          {company?.volume?.paid_by_dest_currency && company.volume.paid_by_dest_currency.length > 0 && (
            <Card>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Volumen por Moneda Destino</Typography>
                <Stack spacing={1.5}>
                  {company.volume.paid_by_dest_currency.map((c, i) => {
                    const maxVal = company.volume.paid_by_dest_currency[0]?.volume || 1;
                    const pct = (c.volume / maxVal) * 100;
                    return (
                      <Box key={c.dest_currency}>
                        <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>{c.dest_currency}</Typography>
                          <Typography variant="body2" sx={{ fontWeight: 700, color: '#4B2E83' }}>{c.volume.toLocaleString('es-VE', { minimumFractionDigits: 2 })}</Typography>
                        </Stack>
                        <Box sx={{ height: 8, borderRadius: 4, backgroundColor: '#E9E3F7', overflow: 'hidden' }}>
                          <Box sx={{ height: '100%', width: `${pct}%`, borderRadius: 4, backgroundColor: COLORS[i % COLORS.length], transition: 'width 0.5s ease' }} />
                        </Box>
                      </Box>
                    );
                  })}
                </Stack>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </Box>
  );
}
