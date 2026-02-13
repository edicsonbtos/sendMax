'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Chip,
  Stack,
  Divider,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  Receipt as ReceiptIcon,
  AccountBalance as WalletIcon,
  AttachMoney as MoneyIcon,
  Warning as WarningIcon,
  Refresh as RefreshIcon,
  Schedule as ClockIcon,
  Verified as VerifiedIcon,
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
} from 'recharts';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

/* ---------------- Helpers ---------------- */
const currencyDecimals = (currency: string) => (['COP', 'VES', 'CLP'].includes(currency) ? 0 : 2);

const formatMoney = (amount: number, currency: string) => {
  const d = currencyDecimals(currency);
  return amount.toLocaleString('es-VE', { minimumFractionDigits: d, maximumFractionDigits: d });
};

const getCurrencySymbol = (currency: string) => {
  const m: Record<string, string> = {
    USD: '$', USDT: '$',
    COP: 'COL$', VES: 'Bs.', CLP: 'CLP$', PEN: 'S/',
    ARS: 'AR$', BRL: 'R$', MXN: 'MX$', BOB: 'Bs',
  };
  return m[currency] || currency;
};

/* ---------------- Types ---------------- */
interface MetricsOverview {
  total_orders: number;
  pending_orders: number;
  completed_orders: number;
  total_volume_usd: number;
  total_profit_usd: number;
  total_profit_real_usd?: number;
  status_counts: Record<string, number>;
  awaiting_paid_proof: number;
}

interface CompanyOverview {
  ok: boolean;
  orders: { total_orders: number; pending_orders: number; completed_orders: number };
  profit: { total_profit_usd: number; total_profit_real_usd?: number };
  origin_wallets: {
    pending_by_currency: Record<string, number>;
    top_pending: { origin_country: string; fiat_currency: string; current_balance: number }[];
  };
  volume: {
    paid_usd_usdt: number;
    paid_by_dest_currency: { dest_currency: string; volume: number; count?: number }[];
  };
}

interface StuckAlert {
  public_id: number;
  origin_country: string;
  dest_country: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface AlertsResponse {
  ok: boolean;
  cutoff_utc: string;
  origin_verificando_stuck: StuckAlert[];
  awaiting_paid_proof_stuck: StuckAlert[];
}

interface ProfitDayRaw {
  day: string;
  total_orders: number;
  total_profit: number;
  total_profit_real?: number;
  total_volume: number;
}

interface ProfitDailyResponse {
  days: number;
  profit_by_day: ProfitDayRaw[];
}

interface ProfitDay {
  day: string;
  profit: number;
  profit_real: number;
  orders: number;
  volume: number;
}

type IconComponent = React.ElementType<{ sx?: object }>;

interface StatCardProps {
  title: string;
  value: string | number;
  Icon: IconComponent;
  color: string;
  subtitle?: string;
}

function StatCard({ title, value, Icon, color, subtitle }: StatCardProps) {
  return (
    <Card sx={{ flex: '1 1 calc(25% - 16px)', minWidth: 200 }}>
      <CardContent sx={{ p: 2.5 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
          <Box>
            <Typography variant="body2" sx={{ color: '#64748B', fontSize: '0.8rem', mb: 0.5 }}>
              {title}
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 800, color: '#111827', lineHeight: 1.1 }}>
              {value}
            </Typography>
            {subtitle && (
              <Typography variant="caption" sx={{ color: '#64748B', mt: 0.5, display: 'block' }}>
                {subtitle}
              </Typography>
            )}
          </Box>
          <Box sx={{ backgroundColor: `${color}12`, borderRadius: '14px', p: 1.25, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Icon sx={{ color, fontSize: 26 }} />
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

const STATUS_COLORS: Record<string, string> = {
  PAGADA: '#16A34A',
  CANCELADA: '#DC2626',
  CREADA: '#F59E0B',
  EN_PROCESO: '#2563EB',
  ORIGEN_VERIFICANDO: '#8B5CF6',
  COMPLETADA: '#16A34A',
};

export default function OverviewPage() {
  const { apiKey, setApiKey, clearApiKey } = useAuth();
  const [tempKey, setTempKey] = useState('');

  const [metrics, setMetrics] = useState<MetricsOverview | null>(null);
  const [companyOverview, setCompanyOverview] = useState<CompanyOverview | null>(null);
  const [alerts, setAlerts] = useState<StuckAlert[]>([]);
  const [profitDaily, setProfitDaily] = useState<ProfitDay[]>([]);
  const [statusCounts, setStatusCounts] = useState<{ name: string; value: number; color: string }[]>([]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState<string>('');

  const pendingByCurrency = useMemo(() => {
    const m = companyOverview?.origin_wallets?.pending_by_currency || {};
    return Object.entries(m).sort((a, b) => b[1] - a[1]);
  }, [companyOverview]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const [metricsData, companyData, alertsData, profitData] = await Promise.all([
        apiRequest<MetricsOverview>('/metrics/overview'),
        apiRequest<CompanyOverview>('/metrics/company-overview').catch(() => null),
        apiRequest<AlertsResponse>('/alerts/stuck-30m').catch(() => null),
        apiRequest<ProfitDailyResponse>('/metrics/profit_daily?days=7').catch(() => null),
      ]);

      setMetrics(metricsData);
      setCompanyOverview(companyData);

      // Alerts
      const allAlerts: StuckAlert[] = [];
      if (alertsData) {
        if (alertsData.origin_verificando_stuck) allAlerts.push(...alertsData.origin_verificando_stuck);
        if (alertsData.awaiting_paid_proof_stuck) allAlerts.push(...alertsData.awaiting_paid_proof_stuck);
      }
      setAlerts(allAlerts);

      // Profit daily
      if (profitData?.profit_by_day) {
        setProfitDaily(
          profitData.profit_by_day.map((d) => ({
            day: new Date(d.day).toLocaleDateString('es-VE', { weekday: 'short', day: 'numeric' }),
            profit: d.total_profit || 0,
            profit_real: d.total_profit_real || 0,
            orders: d.total_orders || 0,
            volume: d.total_volume || 0,
          }))
        );
      }

      // Status counts
      if (metricsData?.status_counts) {
        setStatusCounts(
          Object.entries(metricsData.status_counts)
            .filter(([, value]) => (value || 0) > 0)
            .map(([name, value]) => ({
              name,
              value: Number(value || 0),
              color: STATUS_COLORS[name] || '#6B7280',
            }))
        );
      }

      setLastUpdated(new Date().toLocaleTimeString('es-VE'));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error desconocido';
      setError(message);
      if (message === 'API_KEY_INVALID') clearApiKey();
    } finally {
      setLoading(false);
    }
  }, [clearApiKey]);

  useEffect(() => {
    if (apiKey) fetchData();
  }, [apiKey, fetchData]);

  const saveKey = () => {
    setApiKey(tempKey);
    setError('');
  };

  if (!apiKey) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '80vh' }}>
        <Card sx={{ maxWidth: 480, width: '100%' }}>
          <CardContent sx={{ p: 4 }}>
            <Box sx={{ textAlign: 'center', mb: 3 }}>
              <Box component="img" src="/logo.png" alt="Sendmax" sx={{ height: 48, width: 'auto', mb: 2 }} />
              <Typography variant="h5" sx={{ fontWeight: 700, color: '#4B2E83', mb: 0.5 }}>
                Sendmax Backoffice
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Ingresa tu API Key para acceder al panel de control
              </Typography>
            </Box>
            <Divider sx={{ my: 2 }} />
            <Stack spacing={2.5}>
              <TextField
                fullWidth
                type="password"
                label="API Key"
                value={tempKey}
                onChange={(e) => setTempKey(e.target.value)}
                helperText="La clave se guarda localmente en tu navegador"
                onKeyDown={(e) => e.key === 'Enter' && tempKey && saveKey()}
              />
              <Button variant="contained" onClick={saveKey} disabled={!tempKey} size="large" fullWidth sx={{ py: 1.5 }}>
                Acceder al panel
              </Button>
            </Stack>
            {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
          </CardContent>
        </Card>
      </Box>
    );
  }

  const profitTheoretical = metrics?.total_profit_usd || 0;
  const profitReal = metrics?.total_profit_real_usd || 0;

  return (
    <Box className="fade-in">
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: '#111827' }}>Dashboard</Typography>
          <Typography variant="body2" sx={{ color: '#64748B', mt: 0.5 }}>
            {`Vista general de operaciones Sendmax${lastUpdated ? ` | Actualizado: ${lastUpdated}` : ''}`}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Tooltip title="Actualizar datos">
            <IconButton onClick={fetchData} disabled={loading} sx={{ color: '#4B2E83' }}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          <Button variant="outlined" size="small" onClick={clearApiKey}>Cambiar Key</Button>
        </Stack>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress sx={{ color: '#4B2E83' }} />
        </Box>
      )}

      {metrics && !loading && (
        <>
          <Stack direction="row" spacing={2.5} sx={{ mb: 4, flexWrap: 'wrap', gap: 2 }}>
            <StatCard title="Total Ordenes" value={metrics.total_orders} Icon={ReceiptIcon} color="#4B2E83" subtitle={`${metrics.completed_orders} pagadas`} />
            <StatCard title="Pendientes" value={metrics.pending_orders} Icon={TrendingUpIcon} color="#F59E0B" subtitle={metrics.awaiting_paid_proof > 0 ? `${metrics.awaiting_paid_proof} esperando comprobante` : 'Requieren atencion'} />

            <StatCard
              title="Profit Teorico (USDT)"
              value={`$${profitTheoretical.toFixed(2)}`}
              Icon={MoneyIcon}
              color="#16A34A"
              subtitle="SUM(orders.profit_usdt) pagadas"
            />
            <StatCard
              title="Profit Real (USDT)"
              value={`$${profitReal.toFixed(2)}`}
              Icon={VerifiedIcon}
              color="#2563EB"
              subtitle="SUM(orders.profit_real_usdt) pagadas"
            />
          </Stack>

          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2.5} sx={{ mb: 4 }}>
            <Card sx={{ flex: 2, minWidth: 0 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ mb: 0.5 }}>Ganancia Diaria (7 dias)</Typography>
                <Typography variant="caption" sx={{ color: '#64748B', display: 'block', mb: 2 }}>
                  Teorico vs Real (si hay trades)
                </Typography>

                {profitDaily.length > 0 ? (
                  <ResponsiveContainer width="100%" height={260}>
                    <AreaChart data={profitDaily}>
                      <defs>
                        <linearGradient id="profitTheo" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#16A34A" stopOpacity={0.22} />
                          <stop offset="100%" stopColor="#16A34A" stopOpacity={0.02} />
                        </linearGradient>
                        <linearGradient id="profitReal" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#2563EB" stopOpacity={0.22} />
                          <stop offset="100%" stopColor="#2563EB" stopOpacity={0.02} />
                        </linearGradient>
                      </defs>

                      <CartesianGrid strokeDasharray="3 3" stroke="#E9E3F7" vertical={false} />
                      <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#64748B' }} axisLine={{ stroke: '#E9E3F7' }} tickLine={false} />
                      <YAxis tick={{ fontSize: 11, fill: '#64748B' }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `$${v}`} />

                      <RechartsTooltip
                        contentStyle={{ borderRadius: 12, border: '1px solid #E9E3F7', boxShadow: '0 8px 24px rgba(17,24,39,.06)', fontSize: 13 }}
                        formatter={(value?: unknown, name?: string) => {
                          const n = typeof value === 'number' ? value : Number(value ?? 0);
                          const label = name === 'profit' ? 'Profit teorico' : name === 'profit_real' ? 'Profit real' : (name || '');
                          return [`$${n.toFixed(2)}`, label];
                        }}
                      />

                      <Area type="monotone" dataKey="profit" stroke="#16A34A" strokeWidth={2.5} fill="url(#profitTheo)" dot={false} />
                      <Area type="monotone" dataKey="profit_real" stroke="#2563EB" strokeWidth={2.5} fill="url(#profitReal)" dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <Box sx={{ py: 6, textAlign: 'center' }}>
                    <Typography variant="body2" color="text.secondary">No hay datos</Typography>
                  </Box>
                )}
              </CardContent>
            </Card>

            <Card sx={{ flex: 1, minWidth: 280 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ mb: 0.5 }}>Ordenes por Status</Typography>
                <Typography variant="caption" sx={{ color: '#64748B', display: 'block', mb: 2 }}>Distribucion actual</Typography>

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
                      {statusCounts.map((s) => (
                        <Stack key={s.name} direction="row" justifyContent="space-between" alignItems="center">
                          <Stack direction="row" spacing={1} alignItems="center">
                            <Box sx={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: s.color }} />
                            <Typography variant="body2" sx={{ fontSize: '0.8rem' }}>{s.name}</Typography>
                          </Stack>
                          <Chip label={s.value} size="small" sx={{ backgroundColor: `${s.color}15`, color: s.color, fontWeight: 700, fontSize: '0.75rem', height: 22 }} />
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

          {/* Pending by currency */}
          {pendingByCurrency.length > 0 && (
            <Card sx={{ mb: 4 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 800 }}>Saldos Pendientes (por moneda)</Typography>
                <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
                  {pendingByCurrency.map(([cur, amt]) => (
                    <Chip
                      key={cur}
                      label={`${getCurrencySymbol(cur)} ${cur}: ${formatMoney(amt, cur)}`}
                      sx={{ fontWeight: 800, backgroundColor: '#EFEAFF', color: '#4B2E83' }}
                    />
                  ))}
                </Stack>
              </CardContent>
            </Card>
          )}

          {/* Top pending wallets */}
          {companyOverview?.origin_wallets?.top_pending?.length ? (
            <Card sx={{ mb: 4 }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ mb: 2, fontWeight: 800 }}>Top Billeteras con Saldo Pendiente</Typography>
                <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap', gap: 1 }}>
                  {companyOverview.origin_wallets.top_pending.map((w, i) => (
                    <Card key={i} variant="outlined" sx={{ minWidth: 200, flex: '1 1 calc(25% - 16px)' }}>
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
            <Card sx={{ border: '1px solid #F59E0B', backgroundColor: '#FFFBF0' }}>
              <CardContent sx={{ p: 3 }}>
                <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 2 }}>
                  <WarningIcon sx={{ color: '#F59E0B' }} />
                  <Typography variant="h6" sx={{ fontWeight: 800 }}>Alertas Activas</Typography>
                  <Chip label={`${alerts.length} orden${alerts.length > 1 ? 'es' : ''}`} size="small" sx={{ backgroundColor: '#FFF5E6', color: '#F59E0B', fontWeight: 800, border: '1px solid #F59E0B' }} />
                </Stack>

                <Typography variant="body2" sx={{ color: '#64748B', mb: 2 }}>
                  Ordenes estancadas por mas de 30 minutos sin cambio de status
                </Typography>

                <Stack spacing={1.5}>
                  {alerts.map((a) => {
                    const minutesStuck = Math.floor((Date.now() - new Date(a.updated_at).getTime()) / 60000);
                    return (
                      <Alert severity="warning" key={a.public_id} sx={{ backgroundColor: '#FFF5E6', border: '1px solid #FBBF24' }}>
                        <Stack direction="row" spacing={2} alignItems="center" sx={{ flexWrap: 'wrap', gap: 1 }}>
                          <Chip label={`#${a.public_id}`} size="small" sx={{ fontWeight: 800, fontFamily: 'monospace' }} />
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>{a.status}</Typography>
                          <Typography variant="body2" sx={{ color: '#64748B' }}>{`${a.origin_country} → ${a.dest_country}`}</Typography>
                          <Chip icon={<ClockIcon sx={{ fontSize: 14 }} />} label={`${minutesStuck} min`} size="small" color="warning" variant="outlined" sx={{ fontWeight: 700 }} />
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
