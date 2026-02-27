'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  Box, Typography, Card, CardContent, Alert, CircularProgress,
  Chip, Stack, Divider, IconButton, Tooltip, TextField, MenuItem,
  Button, Fade,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon, Receipt as ReceiptIcon,
  AttachMoney as MoneyIcon, Warning as WarningIcon,
  Refresh as RefreshIcon, Schedule as ClockIcon,
  Verified as VerifiedIcon, AccountBalance as VaultIcon,
  Download as DownloadIcon, FilterList as FilterIcon,
} from '@mui/icons-material';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer,
  BarChart, Bar, Cell,
} from 'recharts';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest, API_BASE, getToken, getApiKey } from '@/lib/api';

/* ═══════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════ */

const currencyDecimals = (c: string) => ['COP','VES','CLP'].includes(c) ? 0 : 2;
const formatMoney = (a: number, c: string) => {
  const d = currencyDecimals(c);
  return a.toLocaleString('es-VE', { minimumFractionDigits: d, maximumFractionDigits: d });
};
const formatCompact = (n: number): string => {
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toFixed(2);
};
const getCurrencySymbol = (c: string) => {
  const m: Record<string,string> = {USD:'$',USDT:'$',COP:'COL$',VES:'Bs.',CLP:'CLP$',PEN:'S/',ARS:'AR$',BRL:'R$',MXN:'MX$',BOB:'Bs'};
  return m[c]||c;
};

function downloadCSV(endpoint: string, filename: string, params: Record<string,string>) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v) qs.set(k, v); });
  const url = `${API_BASE}${endpoint}?${qs.toString()}`;
  const token = getToken();
  const apiKey = getApiKey();

  fetch(url, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(apiKey ? { 'X-API-KEY': apiKey } : {}),
    },
  })
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.blob();
    })
    .then(blob => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      URL.revokeObjectURL(a.href);
    })
    .catch(err => alert('Error descargando: ' + err.message));
}

/* ═══════════════════════════════════════════════════
   Interfaces
   ═══════════════════════════════════════════════════ */

interface CompanyOverview {
  ok: boolean;
  orders: { total_orders: number; pending_orders: number; completed_orders: number };
  profit: { total_profit_usd: number; total_profit_real_usd?: number };
  origin_wallets: {
    pending_by_currency: Record<string,number>;
    top_pending: { origin_country: string; fiat_currency: string; current_balance: number }[];
  } | null;
  volume: {
    paid_usd_usdt: number;
    total_volume_origin?: number;
    paid_by_dest_currency: { dest_currency: string; volume: number; count?: number }[];
  };
}
interface MetricsOverview {
  total_orders: number; pending_orders: number; completed_orders: number;
  total_volume_usd: number; total_profit_usd: number; total_profit_real_usd?: number;
  status_counts: Record<string,number>; awaiting_paid_proof: number;
}
interface StuckAlert { public_id: number; origin_country: string; dest_country: string; status: string; created_at: string; updated_at: string }
interface AlertsResponse { ok: boolean; cutoff_utc: string; origin_verificando_stuck: StuckAlert[]; awaiting_paid_proof_stuck: StuckAlert[] }
interface ProfitDayRaw { day: string; total_orders: number; total_profit: number; total_profit_real?: number; total_volume: number }
interface ProfitDailyResponse { days: number; profit_by_day: ProfitDayRaw[] }
interface ProfitDay { day: string; profit: number; profit_real: number; orders: number; volume: number }

/* ═══════════════════════════════════════════════════
   KPI Card Component
   ═══════════════════════════════════════════════════ */

type IconComponent = React.ElementType<{sx?: object}>;

function KPICard({ title, value, subtitle, Icon, gradient, delay = 0 }: {
  title: string; value: string; subtitle?: string;
  Icon: IconComponent; gradient: string; delay?: number;
}) {
  return (
    <Fade in timeout={600} style={{ transitionDelay: `${delay}ms` }}>
      <Card sx={{
        flex: '1 1 calc(25% - 18px)', minWidth: 220, position: 'relative', overflow: 'hidden',
        background: gradient,
        borderRadius: '20px', border: 'none',
        boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
        transition: 'transform 0.2s, box-shadow 0.2s',
        '&:hover': { transform: 'translateY(-4px)', boxShadow: '0 16px 48px rgba(0,0,0,0.12)' },
      }}>
        <CardContent sx={{ p: 3, position: 'relative', zIndex: 1 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
            <Box>
              <Typography sx={{ color: 'rgba(255,255,255,0.8)', fontSize: '0.78rem', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase', mb: 0.5 }}>
                {title}
              </Typography>
              <Typography sx={{ color: '#fff', fontWeight: 900, fontSize: '1.85rem', lineHeight: 1.1, mb: 0.5 }}>
                {value}
              </Typography>
              {subtitle && (
                <Typography sx={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.75rem', fontWeight: 500 }}>
                  {subtitle}
                </Typography>
              )}
            </Box>
            <Box sx={{
              backgroundColor: 'rgba(255,255,255,0.18)', borderRadius: '16px',
              p: 1.5, display: 'flex', backdropFilter: 'blur(8px)',
            }}>
              <Icon sx={{ color: '#fff', fontSize: 28 }} />
            </Box>
          </Stack>
        </CardContent>
        {/* Decorative circle */}
        <Box sx={{
          position: 'absolute', top: -30, right: -30, width: 120, height: 120,
          borderRadius: '50%', backgroundColor: 'rgba(255,255,255,0.06)',
        }} />
      </Card>
    </Fade>
  );
}

/* ═══════════════════════════════════════════════════
   Filters Bar
   ═══════════════════════════════════════════════════ */

const COUNTRIES = ['','CHILE','COLOMBIA','VENEZUELA','PERU','ARGENTINA','MEXICO','BRASIL','BOLIVIA','PANAMA','USA'];
const COUNTRY_LABELS: Record<string,string> = {'':'Todos los países','CHILE':'🇨🇱 Chile','COLOMBIA':'🇨🇴 Colombia','VENEZUELA':'🇻🇪 Venezuela','PERU':'🇵🇪 Perú','ARGENTINA':'🇦🇷 Argentina','MEXICO':'🇲🇽 México','BRASIL':'🇧🇷 Brasil','BOLIVIA':'🇧🇴 Bolivia','PANAMA':'🇵🇦 Panamá','USA':'🇺🇸 USA'};

function FiltersBar({ dateFrom, dateTo, country, onDateFrom, onDateTo, onCountry, onExportOrders, onExportWallets }: {
  dateFrom: string; dateTo: string; country: string;
  onDateFrom: (v: string) => void; onDateTo: (v: string) => void; onCountry: (v: string) => void;
  onExportOrders: () => void; onExportWallets: () => void;
}) {
  return (
    <Card sx={{ mb: 3, borderRadius: '16px', boxShadow: '0 4px 16px rgba(0,0,0,0.04)' }}>
      <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
        <Stack direction="row" alignItems="center" spacing={2} sx={{ flexWrap: 'wrap', gap: 1.5 }}>
          <Stack direction="row" alignItems="center" spacing={0.5}>
            <FilterIcon sx={{ color: '#64748B', fontSize: 20 }} />
            <Typography sx={{ color: '#64748B', fontSize: '0.8rem', fontWeight: 700 }}>Filtros</Typography>
          </Stack>
          <TextField
            type="date" size="small" label="Desde" value={dateFrom}
            onChange={e => onDateFrom(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ width: 160, '& .MuiOutlinedInput-root': { borderRadius: '12px' } }}
          />
          <TextField
            type="date" size="small" label="Hasta" value={dateTo}
            onChange={e => onDateTo(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ width: 160, '& .MuiOutlinedInput-root': { borderRadius: '12px' } }}
          />
          <TextField
            select size="small" label="País origen" value={country}
            onChange={e => onCountry(e.target.value)}
            sx={{ width: 180, '& .MuiOutlinedInput-root': { borderRadius: '12px' } }}
          >
            {COUNTRIES.map(c => (
              <MenuItem key={c} value={c}>{COUNTRY_LABELS[c] || c}</MenuItem>
            ))}
          </TextField>
          <Box sx={{ flex: 1 }} />
          <Tooltip title="Exportar órdenes CSV">
            <Button
              size="small" variant="outlined" startIcon={<DownloadIcon />}
              onClick={onExportOrders}
              sx={{ borderRadius: '12px', textTransform: 'none', fontWeight: 600, borderColor: '#4B2E83', color: '#4B2E83' }}
            >
              Órdenes
            </Button>
          </Tooltip>
          <Tooltip title="Exportar cierres billetera CSV">
            <Button
              size="small" variant="outlined" startIcon={<DownloadIcon />}
              onClick={onExportWallets}
              sx={{ borderRadius: '12px', textTransform: 'none', fontWeight: 600, borderColor: '#16A34A', color: '#16A34A' }}
            >
              Cierres
            </Button>
          </Tooltip>
        </Stack>
      </CardContent>
    </Card>
  );
}

/* ═══════════════════════════════════════════════════
   Status Colors
   ═══════════════════════════════════════════════════ */

const STATUS_COLORS: Record<string,string> = {
  PAGADA: '#16A34A', CANCELADA: '#DC2626', CREADA: '#F59E0B',
  EN_PROCESO: '#2563EB', ORIGEN_VERIFICANDO: '#8B5CF6', COMPLETADA: '#16A34A',
};

/* ═══════════════════════════════════════════════════
   MAIN PAGE
   ═══════════════════════════════════════════════════ */

export default function DashboardPage() {
  const { token } = useAuth();

  // -- Filters (stable refs to avoid re-renders) --
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [country, setCountry] = useState('');

  // -- Data --
  const [metrics, setMetrics] = useState<MetricsOverview | null>(null);
  const [companyOverview, setCompanyOverview] = useState<CompanyOverview | null>(null);
  const [alerts, setAlerts] = useState<StuckAlert[]>([]);
  const [profitDaily, setProfitDaily] = useState<ProfitDay[]>([]);
  const [statusCounts, setStatusCounts] = useState<{name:string;value:number;color:string}[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState('');

  // Debounce filter changes
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchData = useCallback(async (df = dateFrom, dt = dateTo, oc = country) => {
    setLoading(true); setError('');
    try {
      const qp = new URLSearchParams();
      if (df) qp.set('date_from', df);
      if (dt) qp.set('date_to', dt);
      if (oc) qp.set('origin_country', oc);
      const qs = qp.toString() ? `?${qp.toString()}` : '';

      const [metricsData, companyData, alertsData, profitData] = await Promise.all([
        apiRequest<MetricsOverview>('/metrics/overview'),
        apiRequest<CompanyOverview>(`/metrics/company-overview${qs}`).catch(() => null),
        apiRequest<AlertsResponse>('/alerts/stuck-30m').catch(() => null),
        apiRequest<ProfitDailyResponse>('/metrics/profit_daily?days=7').catch(() => null),
      ]);

      setMetrics(metricsData);
      setCompanyOverview(companyData);

      const allAlerts: StuckAlert[] = [];
      if (alertsData) {
        if (alertsData.origin_verificando_stuck) allAlerts.push(...alertsData.origin_verificando_stuck);
        if (alertsData.awaiting_paid_proof_stuck) allAlerts.push(...alertsData.awaiting_paid_proof_stuck);
      }
      setAlerts(allAlerts);

      if (profitData?.profit_by_day) {
        setProfitDaily(profitData.profit_by_day.map(d => ({
          day: new Date(d.day).toLocaleDateString('es-VE', { weekday: 'short', day: 'numeric' }),
          profit: d.total_profit || 0,
          profit_real: d.total_profit_real || 0,
          orders: d.total_orders || 0,
          volume: d.total_volume || 0,
        })));
      }
      if (metricsData?.status_counts) {
        setStatusCounts(
          Object.entries(metricsData.status_counts)
            .filter(([, v]) => (v || 0) > 0)
            .map(([name, value]) => ({ name, value: Number(value || 0), color: STATUS_COLORS[name] || '#6B7280' }))
        );
      }
      setLastUpdated(new Date().toLocaleTimeString('es-VE'));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error');
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, country]);

  // Initial load
  useEffect(() => { if (token) fetchData(); }, [token, fetchData]);

  // Debounced filter effect
  const onFilterChange = useCallback((df: string, dt: string, oc: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => fetchData(df, dt, oc), 400);
  }, [fetchData]);

  const handleDateFrom = (v: string) => { setDateFrom(v); onFilterChange(v, dateTo, country); };
  const handleDateTo = (v: string) => { setDateTo(v); onFilterChange(dateFrom, v, country); };
  const handleCountry = (v: string) => { setCountry(v); onFilterChange(dateFrom, dateTo, v); };

  // Export handlers
  const exportOrders = () => downloadCSV('/metrics/export-orders', `ordenes_${dateFrom || 'all'}_${dateTo || 'today'}.csv`, { date_from: dateFrom, date_to: dateTo, origin_country: country });
  const exportWallets = () => downloadCSV('/origin-wallets/export', `cierres_${dateFrom || 'all'}_${dateTo || 'today'}.csv`, { date_from: dateFrom, date_to: dateTo, origin_country: country });

  // Derived KPIs
  const co = companyOverview;
  const volumeUSD = co?.volume?.paid_usd_usdt || 0;
  const profitReal = co?.profit?.total_profit_real_usd || metrics?.total_profit_real_usd || 0;
  const completedOrders = co?.orders?.completed_orders || metrics?.completed_orders || 0;
  const vaultBalance = useMemo(() => {
    if (!co?.origin_wallets?.pending_by_currency) return 0;
    return Object.values(co.origin_wallets.pending_by_currency).reduce((s, v) => s + v, 0);
  }, [co]);

  const pendingByCurrency = useMemo(() => {
    const m = co?.origin_wallets?.pending_by_currency || {};
    return Object.entries(m).sort((a, b) => b[1] - a[1]);
  }, [co]);

  if (!token) return null;

  return (
    <Box className="fade-in">
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 900, color: '#111827', letterSpacing: '-0.02em' }}>
            Dashboard Ejecutivo
          </Typography>
          <Typography variant="body2" sx={{ color: '#64748B', mt: 0.25 }}>
            {'Centro de decisiones SendMax' + (lastUpdated ? ` · ${lastUpdated}` : '')}
          </Typography>
        </Box>
        <Tooltip title="Actualizar datos">
          <IconButton onClick={() => fetchData()} disabled={loading} sx={{ color: '#4B2E83', backgroundColor: '#EFEAFF', '&:hover': { backgroundColor: '#D8CCFF' } }}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 3, borderRadius: '12px' }}>{error}</Alert>}

      {/* Filters Bar */}
      <FiltersBar
        dateFrom={dateFrom} dateTo={dateTo} country={country}
        onDateFrom={handleDateFrom} onDateTo={handleDateTo} onCountry={handleCountry}
        onExportOrders={exportOrders} onExportWallets={exportWallets}
      />

      {loading && <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress sx={{ color: '#4B2E83' }} /></Box>}

      {metrics && !loading && (
        <>
          {/* 4 KPI Cards */}
          <Stack direction="row" spacing={2.5} sx={{ mb: 4, flexWrap: 'wrap', gap: 2 }}>
            <KPICard
              title="Volumen Total (USD)"
              value={`$${formatCompact(volumeUSD)}`}
              subtitle={co?.volume?.total_volume_origin ? `${formatCompact(co.volume.total_volume_origin)} moneda origen` : undefined}
              Icon={TrendingUpIcon}
              gradient="linear-gradient(135deg, #4B2E83 0%, #7C3AED 100%)"
              delay={0}
            />
            <KPICard
              title="Utilidad Neta Real"
              value={`$${formatCompact(profitReal)}`}
              subtitle={`Teórica: $${formatCompact(co?.profit?.total_profit_usd || 0)}`}
              Icon={VerifiedIcon}
              gradient="linear-gradient(135deg, #059669 0%, #16A34A 100%)"
              delay={80}
            />
            <KPICard
              title="Órdenes Completadas"
              value={completedOrders.toLocaleString()}
              subtitle={`${metrics.pending_orders} pendientes · ${metrics.total_orders} total`}
              Icon={ReceiptIcon}
              gradient="linear-gradient(135deg, #2563EB 0%, #3B82F6 100%)"
              delay={160}
            />
            <KPICard
              title="Balance Total Bóveda"
              value={pendingByCurrency.length > 0 ? `${pendingByCurrency.length} monedas` : '$0'}
              subtitle={vaultBalance > 0 ? `Total equiv. ${formatCompact(vaultBalance)}` : 'Sin fondos pendientes'}
              Icon={VaultIcon}
              gradient="linear-gradient(135deg, #D97706 0%, #F59E0B 100%)"
              delay={240}
            />
          </Stack>

          {/* Charts Row */}
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2.5} sx={{ mb: 4 }}>
            {/* Profit Chart */}
            <Card sx={{ flex: 2, minWidth: 0, borderRadius: '20px', boxShadow: '0 4px 24px rgba(0,0,0,0.05)' }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 800, mb: 0.5 }}>Ganancia Diaria (7 días)</Typography>
                <Typography variant="caption" sx={{ color: '#64748B', display: 'block', mb: 2 }}>
                  Teórica vs Utilidad Neta Real
                </Typography>
                {profitDaily.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <AreaChart data={profitDaily}>
                      <defs>
                        <linearGradient id="gTheo" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#16A34A" stopOpacity={0.22} />
                          <stop offset="100%" stopColor="#16A34A" stopOpacity={0.02} />
                        </linearGradient>
                        <linearGradient id="gReal" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#2563EB" stopOpacity={0.22} />
                          <stop offset="100%" stopColor="#2563EB" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E9E3F7" vertical={false} />
                      <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={{ stroke: '#E9E3F7' }} tickLine={false} />
                      <YAxis tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} tickFormatter={(v: number) => '$' + v} />
                      <RechartsTooltip
                        contentStyle={{ borderRadius: 12, border: '1px solid #E9E3F7', boxShadow: '0 8px 24px rgba(17,24,39,.06)', fontSize: 13 }}
                        formatter={(value?: unknown, name?: string) => {
                          const n = typeof value === 'number' ? value : Number(value ?? 0);
                          const label = name === 'profit' ? 'Profit teórico' : name === 'profit_real' ? 'Utilidad Neta' : (name || '');
                          return ['$' + n.toFixed(2), label];
                        }}
                      />
                      <Area type="monotone" dataKey="profit" stroke="#16A34A" strokeWidth={2.5} fill="url(#gTheo)" dot={false} />
                      <Area type="monotone" dataKey="profit_real" stroke="#2563EB" strokeWidth={2.5} fill="url(#gReal)" dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <Box sx={{ py: 6, textAlign: 'center' }}>
                    <Typography variant="body2" color="text.secondary">No hay datos</Typography>
                  </Box>
                )}
              </CardContent>
            </Card>

            {/* Status Distribution */}
            <Card sx={{ flex: 1, minWidth: 280, borderRadius: '20px', boxShadow: '0 4px 24px rgba(0,0,0,0.05)' }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 800, mb: 0.5 }}>Órdenes por Status</Typography>
                <Typography variant="caption" sx={{ color: '#64748B', display: 'block', mb: 2 }}>Distribución actual</Typography>
                {statusCounts.length > 0 ? (
                  <>
                    <ResponsiveContainer width="100%" height={160}>
                      <BarChart data={statusCounts} layout="vertical">
                        <XAxis type="number" hide />
                        <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: '#475569' }} axisLine={false} tickLine={false} width={140} />
                        <RechartsTooltip contentStyle={{ borderRadius: 12, border: '1px solid #E9E3F7', fontSize: 13 }} />
                        <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={20}>
                          {statusCounts.map((entry, index) => (<Cell key={index} fill={entry.color} />))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                    <Divider sx={{ my: 1.5 }} />
                    <Stack spacing={1}>
                      {statusCounts.map(s => (
                        <Stack key={s.name} direction="row" justifyContent="space-between" alignItems="center">
                          <Stack direction="row" spacing={1} alignItems="center">
                            <Box sx={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: s.color }} />
                            <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>{s.name}</Typography>
                          </Stack>
                          <Chip label={s.value} size="small" sx={{ backgroundColor: s.color + '15', color: s.color, fontWeight: 700, fontSize: '0.75rem', height: 22 }} />
                        </Stack>
                      ))}
                    </Stack>
                  </>
                ) : (
                  <Box sx={{ py: 6, textAlign: 'center' }}>
                    <Typography variant="body2" color="text.secondary">Sin datos</Typography>
                  </Box>
                )}
              </CardContent>
            </Card>
          </Stack>

          {/* Vault Balance Cards */}
          {pendingByCurrency.length > 0 && (
            <Card sx={{ mb: 4, borderRadius: '20px', boxShadow: '0 4px 24px rgba(0,0,0,0.05)' }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 800 }}>Saldos Pendientes (por moneda)</Typography>
                <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
                  {pendingByCurrency.map(([cur, amt]) => (
                    <Chip key={cur} label={`${getCurrencySymbol(cur)} ${cur}: ${formatMoney(amt, cur)}`}
                      sx={{ fontWeight: 800, backgroundColor: '#EFEAFF', color: '#4B2E83', borderRadius: '12px', height: 32, fontSize: '0.82rem' }}
                    />
                  ))}
                </Stack>
              </CardContent>
            </Card>
          )}

          {/* Top Pending Wallets */}
          {co?.origin_wallets?.top_pending?.length ? (
            <Card sx={{ mb: 4, borderRadius: '20px', boxShadow: '0 4px 24px rgba(0,0,0,0.05)' }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 800 }}>Top Billeteras con Saldo Pendiente</Typography>
                <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap', gap: 1 }}>
                  {co.origin_wallets.top_pending.map((w, i) => (
                    <Card key={i} variant="outlined" sx={{ minWidth: 200, flex: '1 1 calc(25% - 16px)', borderRadius: '14px' }}>
                      <CardContent sx={{ p: 2 }}>
                        <Typography variant="body2" sx={{ color: '#64748B', fontSize: '0.8rem' }}>{w.origin_country}</Typography>
                        <Typography variant="h5" sx={{ fontWeight: 800, color: '#111827', mt: 0.5 }}>
                          {getCurrencySymbol(w.fiat_currency) + ' ' + formatMoney(w.current_balance, w.fiat_currency)}
                        </Typography>
                        <Chip label={w.fiat_currency} size="small" sx={{ mt: 0.5, fontWeight: 800 }} />
                      </CardContent>
                    </Card>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          ) : null}

          {/* Alerts */}
          {alerts.length > 0 && (
            <Card sx={{ border: '1px solid #F59E0B', backgroundColor: '#FFFBF0', borderRadius: '20px' }}>
              <CardContent sx={{ p: 3 }}>
                <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 2 }}>
                  <WarningIcon sx={{ color: '#F59E0B' }} />
                  <Typography variant="h6" sx={{ fontWeight: 800 }}>Alertas Activas</Typography>
                  <Chip label={`${alerts.length} orden${alerts.length > 1 ? 'es' : ''}`} size="small"
                    sx={{ backgroundColor: '#FFF5E6', color: '#F59E0B', fontWeight: 800, border: '1px solid #F59E0B' }}
                  />
                </Stack>
                <Typography variant="body2" sx={{ color: '#64748B', mb: 2 }}>Órdenes estancadas por más de 30 minutos</Typography>
                <Stack spacing={1.5}>
                  {alerts.map(a => {
                    const min = Math.floor((Date.now() - new Date(a.updated_at).getTime()) / 60000);
                    return (
                      <Alert severity="warning" key={a.public_id} sx={{ backgroundColor: '#FFF5E6', border: '1px solid #FBBF24', borderRadius: '12px' }}>
                        <Stack direction="row" spacing={2} alignItems="center" sx={{ flexWrap: 'wrap', gap: 1 }}>
                          <Chip label={`#${a.public_id}`} size="small" sx={{ fontWeight: 800, fontFamily: 'monospace' }} />
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>{a.status}</Typography>
                          <Typography variant="body2" sx={{ color: '#64748B' }}>{a.origin_country} › {a.dest_country}</Typography>
                          <Chip icon={<ClockIcon sx={{ fontSize: 14 }} />} label={`${min} min`} size="small" color="warning" variant="outlined" sx={{ fontWeight: 700 }} />
                        </Stack>
                      </Alert>
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
