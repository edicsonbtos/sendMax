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
  Tabs,
  Tab,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  TrendingUp as ProfitIcon,
  Receipt as OrderIcon,
  AttachMoney as MoneyIcon,
  ShowChart as ChartIcon,
  Download as DownloadIcon,
  People as PeopleIcon,
  CurrencyExchange as P2PIcon,
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

/* ============ Types ============ */
interface MetricsOverview {
  total_orders: number;
  pending_orders: number;
  completed_orders: number;
  total_profit_usd: number;
  total_profit_real_usd: number;
  status_counts: Record<string, number>;
  awaiting_paid_proof: number;
}

interface ProfitDay {
  day: string;
  profit: number;
  profit_real: number;
  orders: number;
  volume: number;
}

interface ProfitDailyResponse {
  days: number;
  profit_by_day: {
    day: string;
    total_orders: number;
    total_profit: number;
    total_profit_real: number;
    total_volume: number;
  }[];
}

interface Corridor {
  corridor: string;
  origin_country: string;
  dest_country: string;
  order_count: number;
  total_profit: number;
  total_profit_real: number;
  total_volume_origin: number;
  total_volume_dest: number;
  avg_profit: number;
  paid_count: number;
  cancelled_count: number;
  conversion_rate: number;
}

interface CorridorsResponse {
  ok: boolean;
  days: number;
  corridors: Corridor[];
}

interface Operator {
  telegram_id: number;
  name: string;
  orders_paid: number;
  total_profit: number;
  total_profit_real: number;
  total_volume: number;
  avg_profit: number;
  countries_operated: number;
  dest_countries: number;
  first_paid: string | null;
  last_paid: string | null;
}

interface OperatorsResponse {
  ok: boolean;
  days: number;
  operators: Operator[];
}

interface P2PPrice {
  country: string;
  fiat: string;
  buy_price: number | null;
  sell_price: number | null;
  spread_pct: number | null;
  source: string | null;
  captured_at: string | null;
  is_verified: boolean;
  methods_used: string | null;
}

interface P2PPricesResponse {
  ok: boolean;
  count: number;
  items: P2PPrice[];
}

/* ============ Helpers ============ */
const COLORS = ['#4B2E83', '#6B46C1', '#2563EB', '#16A34A', '#F59E0B', '#DC2626', '#8B5CF6', '#06B6D4'];
const STATUS_COLORS: Record<string, string> = {
  PAGADA: '#16A34A', CANCELADA: '#DC2626', CREADA: '#F59E0B',
  EN_PROCESO: '#2563EB', ORIGEN_VERIFICANDO: '#8B5CF6',
};

const fmtMoney = (v: number, decimals = 2): string => {
  return v.toLocaleString('es-VE', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
};

const sanitizeCSV = (val: string | number | null | undefined): string => {
  const s = String(val ?? '');
  if (/^[=+\-@\t\r]/.test(s)) return "'" + s;
  if (s.includes(',') || s.includes('"') || s.includes('\n')) return '"' + s.replace(/"/g, '""') + '"';
  return s;
};

const downloadCSV = (headers: string[], rows: (string | number)[][], filename: string) => {
  const csv = [
    headers.map(sanitizeCSV).join(','),
    ...rows.map((r) => r.map(sanitizeCSV).join(',')),
  ].join('\n');
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
};

/* ============ Component ============ */
export default function MetricsPage() {
  const { apiKey } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [days, setDays] = useState(30);
  const [tab, setTab] = useState(0);

  const [overview, setOverview] = useState<MetricsOverview | null>(null);
  const [profitDaily, setProfitDaily] = useState<ProfitDay[]>([]);
  const [corridors, setCorridors] = useState<Corridor[]>([]);
  const [operators, setOperators] = useState<Operator[]>([]);
  const [p2pPrices, setP2pPrices] = useState<P2PPrice[]>([]);
  const [statusData, setStatusData] = useState<{ name: string; value: number; color: string }[]>([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [overviewData, profitData, corridorsData, operatorsData, p2pData] = await Promise.all([
        apiRequest<MetricsOverview>('/metrics/overview'),
        apiRequest<ProfitDailyResponse>(`/metrics/profit_daily?days=${days}`).catch(() => null),
        apiRequest<CorridorsResponse>(`/metrics/corridors?days=${days}`).catch(() => null),
        apiRequest<OperatorsResponse>(`/operators/ranking?days=${days}`).catch(() => null),
        apiRequest<P2PPricesResponse>('/metrics/p2p-prices?limit=20').catch(() => null),
      ]);

      setOverview(overviewData);

      if (profitData?.profit_by_day) {
        setProfitDaily(profitData.profit_by_day.map((d) => ({
          day: new Date(d.day).toLocaleDateString('es-VE', { weekday: 'short', day: 'numeric', month: 'short' }),
          profit: d.total_profit || 0,
          profit_real: d.total_profit_real || 0,
          orders: d.total_orders || 0,
          volume: d.total_volume || 0,
        })));
      }

      if (corridorsData?.corridors) setCorridors(corridorsData.corridors);
      if (operatorsData?.operators) setOperators(operatorsData.operators);
      if (p2pData?.items) setP2pPrices(p2pData.items);

      if (overviewData?.status_counts) {
        setStatusData(
          Object.entries(overviewData.status_counts)
            .filter(([, v]) => v > 0)
            .map(([name, value]) => ({ name, value, color: STATUS_COLORS[name] || '#6B7280' }))
        );
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { if (apiKey) fetchData(); }, [apiKey, fetchData]);

  const totalProfit = overview?.total_profit_usd || 0;
  const totalProfitReal = overview?.total_profit_real_usd || 0;
  const totalOrders = overview?.total_orders || 0;
  const completed = overview?.completed_orders || 0;
  const convRate = totalOrders > 0 ? ((completed / totalOrders) * 100) : 0;
  /* === CSV Exports === */
  const exportCorridorsCSV = () => {
    if (corridors.length === 0) return;
    downloadCSV(
      ['Corredor', 'Ordenes', 'Pagadas', 'Canceladas', 'Conv%', 'Profit Teorico', 'Profit Real', 'Vol Origen', 'Vol Destino'],
      corridors.map((c) => [c.corridor, c.order_count, c.paid_count, c.cancelled_count, c.conversion_rate, c.total_profit.toFixed(2), c.total_profit_real.toFixed(2), c.total_volume_origin.toFixed(2), c.total_volume_dest.toFixed(2)]),
      `corredores_${days}d_${new Date().toISOString().split('T')[0]}.csv`
    );
  };

  const exportOperatorsCSV = () => {
    if (operators.length === 0) return;
    downloadCSV(
      ['Operador', 'Ordenes', 'Profit Teorico', 'Profit Real', 'Avg Profit', 'Paises'],
      operators.map((o) => [o.name, o.orders_paid, o.total_profit.toFixed(2), o.total_profit_real.toFixed(2), o.avg_profit.toFixed(2), o.countries_operated]),
      `operadores_${days}d_${new Date().toISOString().split('T')[0]}.csv`
    );
  };

  const exportP2PCSV = () => {
    if (p2pPrices.length === 0) return;
    downloadCSV(
      ['Pais', 'Moneda', 'Compra', 'Venta', 'Spread%', 'Metodos', 'Verificado', 'Capturado'],
      p2pPrices.map((p) => [p.country, p.fiat, p.buy_price ?? '', p.sell_price ?? '', p.spread_pct?.toFixed(4) ?? '', p.methods_used ?? '', p.is_verified ? 'Si' : 'No', p.captured_at ?? '']),
      `p2p_precios_${new Date().toISOString().split('T')[0]}.csv`
    );
  };

  return (
    <Box className="fade-in">
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>Metricas y Analisis</Typography>
          <Typography variant="body2" sx={{ color: '#64748B', mt: 0.5 }}>Rendimiento, corredores, operadores y precios P2P</Typography>
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
              { title: 'Profit Teorico', value: `$${fmtMoney(totalProfit)}`, icon: <MoneyIcon sx={{ color: '#16A34A', fontSize: 26 }} />, bg: '#16A34A12', sub: 'SUM(profit_usdt) pagadas' },
              { title: 'Profit Real', value: `$${fmtMoney(totalProfitReal)}`, icon: <ChartIcon sx={{ color: '#2563EB', fontSize: 26 }} />, bg: '#2563EB12', sub: 'SUM(profit_real_usdt) pagadas' },
              { title: 'Ordenes Totales', value: totalOrders, icon: <OrderIcon sx={{ color: '#4B2E83', fontSize: 26 }} />, bg: '#4B2E8312', sub: `${completed} pagadas | ${overview?.pending_orders || 0} pendientes` },
              { title: 'Tasa Conversion', value: `${convRate.toFixed(1)}%`, icon: <ProfitIcon sx={{ color: '#F59E0B', fontSize: 26 }} />, bg: '#F59E0B12', sub: `${completed} de ${totalOrders}` },
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

          {/* Tabs */}
          <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
            <Tab icon={<ChartIcon />} label="Profit Diario" iconPosition="start" />
            <Tab icon={<ProfitIcon />} label={`Corredores (${corridors.length})`} iconPosition="start" />
            <Tab icon={<PeopleIcon />} label={`Operadores (${operators.length})`} iconPosition="start" />
            <Tab icon={<P2PIcon />} label={`P2P Precios (${p2pPrices.length})`} iconPosition="start" />
          </Tabs>

          {/* Tab 0: Profit Diario + Status */}
          {tab === 0 && (
            <Stack direction={{ xs: 'column', md: 'row' }} spacing={2.5} sx={{ mb: 3 }}>
              <Card sx={{ flex: 2 }}>
                <CardContent sx={{ p: 3 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>Ganancia Diaria</Typography>
                      <Typography variant="caption" sx={{ color: '#64748B' }}>Teorico vs Real | {days} dias</Typography>
                    </Box>
                    <Chip label={`${days}d`} size="small" sx={{ backgroundColor: '#EFEAFF', color: '#4B2E83', fontWeight: 700 }} />
                  </Stack>
                  {profitDaily.length > 0 ? (
                    <ResponsiveContainer width="100%" height={280}>
                      <AreaChart data={profitDaily}>
                        <defs>
                          <linearGradient id="gradTheo" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#16A34A" stopOpacity={0.22} />
                            <stop offset="100%" stopColor="#16A34A" stopOpacity={0.02} />
                          </linearGradient>
                          <linearGradient id="gradReal" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#2563EB" stopOpacity={0.22} />
                            <stop offset="100%" stopColor="#2563EB" stopOpacity={0.02} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E9E3F7" vertical={false} />
                        <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={{ stroke: '#E9E3F7' }} tickLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `$${v}`} />
                        <RechartsTooltip
                          contentStyle={{ borderRadius: 12, border: '1px solid #E9E3F7', fontSize: 13 }}
                          formatter={(value?: number, name?: string) => {
                            const label = name === 'profit' ? 'Teorico' : name === 'profit_real' ? 'Real' : (name || '');
                            return [`$${Number(value || 0).toFixed(2)}`, label];
                          }}
                        />
                        <Area type="monotone" dataKey="profit" stroke="#16A34A" strokeWidth={2.5} fill="url(#gradTheo)" dot={false} name="profit" />
                        <Area type="monotone" dataKey="profit_real" stroke="#2563EB" strokeWidth={2.5} fill="url(#gradReal)" dot={false} name="profit_real" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : (
                    <Box sx={{ py: 8, textAlign: 'center' }}><Typography variant="body2" color="text.secondary">Sin datos para este periodo</Typography></Box>
                  )}
                </CardContent>
              </Card>

              <Card sx={{ flex: 1, minWidth: 280 }}>
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
          )}

          {/* Tab 1: Corridors */}
          {tab === 1 && (
            <Card sx={{ mb: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>Analisis por Corredor</Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>Rendimiento por ruta | {days} dias</Typography>
                  </Box>
                  <Stack direction="row" spacing={1}>
                    <Chip label={`${corridors.length} rutas`} size="small" sx={{ backgroundColor: '#EFEAFF', color: '#4B2E83', fontWeight: 700 }} />
                    <Button size="small" startIcon={<DownloadIcon />} onClick={exportCorridorsCSV}>CSV</Button>
                  </Stack>
                </Stack>
                <Divider sx={{ mb: 2 }} />
                {corridors.length > 0 ? (
                  <>
                    <ResponsiveContainer width="100%" height={Math.max(200, corridors.length * 40)}>
                      <BarChart data={corridors} layout="vertical" margin={{ left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#E9E3F7" horizontal={false} />
                        <XAxis type="number" tick={{ fontSize: 11, fill: '#64748B' }} tickFormatter={(v: number) => `$${v.toFixed(0)}`} />
                        <YAxis type="category" dataKey="corridor" tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} width={160} />
                        <RechartsTooltip
                          contentStyle={{ borderRadius: 12, fontSize: 13 }}
                          formatter={(value?: number, name?: string) => {
                            const label = name === 'total_profit' ? 'Profit Teorico' : name === 'total_profit_real' ? 'Profit Real' : (name || '');
                            return [`$${Number(value || 0).toFixed(2)}`, label];
                          }}
                        />
                        <Bar dataKey="total_profit" name="total_profit" radius={[0, 6, 6, 0]} barSize={16}>
                          {corridors.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
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
                            <TableCell align="right">Pagadas</TableCell>
                            <TableCell align="right">Conv%</TableCell>
                            <TableCell align="right">Profit Teorico</TableCell>
                            <TableCell align="right">Profit Real</TableCell>
                            <TableCell align="right">Avg Profit</TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {corridors.map((c, i) => (
                            <TableRow key={i} hover>
                              <TableCell sx={{ fontWeight: 600 }}>
                                <Stack direction="row" spacing={1} alignItems="center">
                                  <Box sx={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: COLORS[i % COLORS.length] }} />
                                  <Typography variant="body2">{c.corridor}</Typography>
                                </Stack>
                              </TableCell>
                              <TableCell align="right"><Chip label={c.order_count} size="small" sx={{ fontWeight: 700, height: 22 }} /></TableCell>
                              <TableCell align="right">{c.paid_count}</TableCell>
                              <TableCell align="right">
                                <Chip label={`${c.conversion_rate}%`} size="small" sx={{ fontWeight: 700, height: 22, backgroundColor: c.conversion_rate >= 80 ? '#16A34A15' : c.conversion_rate >= 50 ? '#F59E0B15' : '#DC262615', color: c.conversion_rate >= 80 ? '#16A34A' : c.conversion_rate >= 50 ? '#F59E0B' : '#DC2626' }} />
                              </TableCell>
                              <TableCell align="right" sx={{ fontWeight: 700, color: '#16A34A' }}>${fmtMoney(c.total_profit)}</TableCell>
                              <TableCell align="right" sx={{ fontWeight: 700, color: '#2563EB' }}>${fmtMoney(c.total_profit_real)}</TableCell>
                              <TableCell align="right" sx={{ color: '#64748B' }}>${fmtMoney(c.avg_profit)}</TableCell>
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
          )}

          {/* Tab 2: Operators */}
          {tab === 2 && (
            <Card sx={{ mb: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>Ranking de Operadores</Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>Top operadores por profit | {days} dias</Typography>
                  </Box>
                  <Button size="small" startIcon={<DownloadIcon />} onClick={exportOperatorsCSV}>CSV</Button>
                </Stack>
                <Divider sx={{ mb: 2 }} />
                {operators.length > 0 ? (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>#</TableCell>
                          <TableCell>Operador</TableCell>
                          <TableCell align="right">Ordenes</TableCell>
                          <TableCell align="right">Profit Teorico</TableCell>
                          <TableCell align="right">Profit Real</TableCell>
                          <TableCell align="right">Avg Profit</TableCell>
                          <TableCell align="right">Paises</TableCell>
                          <TableCell align="right">Ultima Op.</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {operators.map((o, i) => (
                          <TableRow key={o.telegram_id} hover>
                            <TableCell>
                              <Chip label={i + 1} size="small" sx={{ fontWeight: 800, backgroundColor: i === 0 ? '#F59E0B15' : '#F1F5F9', color: i === 0 ? '#F59E0B' : '#64748B', height: 24 }} />
                            </TableCell>
                            <TableCell sx={{ fontWeight: 700 }}>{o.name}</TableCell>
                            <TableCell align="right"><Chip label={o.orders_paid} size="small" sx={{ fontWeight: 700, height: 22 }} /></TableCell>
                            <TableCell align="right" sx={{ fontWeight: 700, color: '#16A34A' }}>${fmtMoney(o.total_profit)}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 700, color: '#2563EB' }}>${fmtMoney(o.total_profit_real)}</TableCell>
                            <TableCell align="right" sx={{ color: '#64748B' }}>${fmtMoney(o.avg_profit)}</TableCell>
                            <TableCell align="right">{o.countries_operated}</TableCell>
                            <TableCell align="right" sx={{ fontSize: '0.75rem', color: '#64748B' }}>
                              {o.last_paid ? new Date(o.last_paid).toLocaleDateString('es-VE', { day: 'numeric', month: 'short' }) : '-'}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Box sx={{ py: 6, textAlign: 'center' }}><Typography variant="body2" color="text.secondary">Sin operadores para este periodo</Typography></Box>
                )}
              </CardContent>
            </Card>
          )}

          {/* Tab 3: P2P Prices */}
          {tab === 3 && (
            <Card sx={{ mb: 3 }}>
              <CardContent sx={{ p: 3 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>Precios P2P (Binance)</Typography>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>Ultima captura de precios por pais</Typography>
                  </Box>
                  <Button size="small" startIcon={<DownloadIcon />} onClick={exportP2PCSV}>CSV</Button>
                </Stack>
                <Divider sx={{ mb: 2 }} />
                {p2pPrices.length > 0 ? (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Pais</TableCell>
                          <TableCell>Moneda</TableCell>
                          <TableCell align="right">Compra</TableCell>
                          <TableCell align="right">Venta</TableCell>
                          <TableCell align="right">Spread%</TableCell>
                          <TableCell>Metodos</TableCell>
                          <TableCell align="center">Verificado</TableCell>
                          <TableCell>Capturado</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {p2pPrices.map((p, i) => (
                          <TableRow key={i} hover>
                            <TableCell sx={{ fontWeight: 600 }}>{p.country}</TableCell>
                            <TableCell><Chip label={p.fiat} size="small" sx={{ fontWeight: 700, height: 22 }} /></TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>{p.buy_price != null ? fmtMoney(p.buy_price, p.buy_price < 10 ? 4 : 2) : '-'}</TableCell>
                            <TableCell align="right" sx={{ fontWeight: 600 }}>{p.sell_price != null ? fmtMoney(p.sell_price, p.sell_price < 10 ? 4 : 2) : '-'}</TableCell>
                            <TableCell align="right">
                              {p.spread_pct != null ? (
                                <Chip label={`${p.spread_pct.toFixed(2)}%`} size="small" sx={{ fontWeight: 700, height: 22, backgroundColor: p.spread_pct > 5 ? '#DC262615' : p.spread_pct > 1 ? '#F59E0B15' : '#16A34A15', color: p.spread_pct > 5 ? '#DC2626' : p.spread_pct > 1 ? '#F59E0B' : '#16A34A' }} />
                              ) : '-'}
                            </TableCell>
                            <TableCell sx={{ fontSize: '0.75rem', color: '#64748B' }}>{p.methods_used || '-'}</TableCell>
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
          )}
        </>
      )}
    </Box>
  );
}