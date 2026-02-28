'use client';

/**
 * Admin Dashboard 10x — Dark Tech Premium
 * Design: #050505 bg, glass cards, Electric Cyan (#00E5FF) accents
 * Features: Country Heatmap, Operator Leaderboard with VIP medal,
 *           Vault Radar with blinking alerts, KPI cards, Daily Profit chart
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar,
} from 'recharts';
import { apiRequest, API_BASE, getToken, getApiKey } from '@/lib/api';
import { useAuth } from '@/components/AuthProvider';

/* ═══════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════ */
interface CompanyOverview {
  ok: boolean;
  orders: { total_orders: number; pending_orders: number; completed_orders: number };
  profit: { total_profit_usd: number; total_profit_real_usd?: number };
  origin_wallets: {
    pending_by_currency: Record<string, number>;
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
  status_counts: Record<string, number>; awaiting_paid_proof: number;
}
interface StuckAlert { public_id: number; origin_country: string; dest_country: string; status: string; created_at: string; updated_at: string }
interface AlertsResponse { ok: boolean; cutoff_utc: string; origin_verificando_stuck: StuckAlert[]; awaiting_paid_proof_stuck: StuckAlert[] }
interface ProfitDayRaw { day: string; total_orders: number; total_profit: number; total_profit_real?: number; total_volume: number }
interface ProfitDailyResponse { days: number; profit_by_day: ProfitDayRaw[] }
interface ProfitDay { day: string; profit: number; profit_real: number; orders: number; volume: number }
interface VaultRowData { id: number; name: string; vault_type: string; currency: string; balance: string; alert_threshold: string; is_active: boolean }
interface LeaderboardEntry {
  alias: string; full_name: string; trust_score: number;
  profit_month: string; orders_month: number; kyc_status: string;
}

/* ═══════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════ */
const fmt = (n: number, d = 2) => n.toLocaleString('es-VE', { minimumFractionDigits: d, maximumFractionDigits: d });
const usd = (n: number) => `$${fmt(n)}`;
const compact = (n: number) => {
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toFixed(2);
};

const COUNTRY_FLAG: Record<string, string> = {
  PERU: '🇵🇪', COLOMBIA: '🇨🇴', VENEZUELA: '🇻🇪', CHILE: '🇨🇱',
  ARGENTINA: '🇦🇷', MEXICO: '🇲🇽', USA: '🇺🇸', BRASIL: '🇧🇷',
};
const HEATMAP_COUNTRIES = ['PERU', 'COLOMBIA', 'VENEZUELA', 'CHILE', 'ARGENTINA', 'MEXICO'];
const CYAN = '#00E5FF';
const PURPLE = '#7B2FBE';
const CHART_COLORS = [CYAN, PURPLE, '#f9c74f', '#43aa8b', '#f8961e', '#ff6b6b'];
const RANK_MEDALS = ['🥇', '🥈', '🥉'];

const STATUS_COLORS: Record<string, string> = {
  PAGADA: '#00c896', CANCELADA: '#ff6b6b', CREADA: '#f9c74f',
  EN_PROCESO: CYAN, ORIGEN_VERIFICANDO: PURPLE, COMPLETADA: '#00c896',
};

function downloadCSV(endpoint: string, filename: string, params: Record<string, string>) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v) qs.set(k, v); });
  const url = `${API_BASE}${endpoint}?${qs.toString()}`;
  const token = getToken(); const apiKey = getApiKey();
  fetch(url, { headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(apiKey ? { 'X-API-KEY': apiKey } : {}) } })
    .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.blob(); })
    .then(blob => { const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = filename; a.click(); URL.revokeObjectURL(a.href); })
    .catch(err => alert('Error descargando: ' + err.message));
}

/* ═══════════════════════════════════════════════
   Shared Styles
   ═══════════════════════════════════════════════ */
const S = {
  page: { minHeight: '100vh', background: '#050505', color: '#e0e0e0', fontFamily: "'Inter','Segoe UI',sans-serif", padding: '28px', boxSizing: 'border-box' as const },
  glass: (accent = 'rgba(0,229,255,0.06)') => ({
    background: `linear-gradient(135deg, rgba(255,255,255,0.03), ${accent})`,
    backdropFilter: 'blur(20px)',
    border: `1px solid rgba(0,229,255,0.12)`,
    borderRadius: '20px',
    padding: '24px',
  }),
  h1: { fontSize: '30px', fontWeight: 900, background: 'linear-gradient(135deg, #00E5FF, #7B2FBE)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0, letterSpacing: '-0.5px' },
  label: { fontSize: '10px', fontWeight: 700, letterSpacing: '2px', textTransform: 'uppercase' as const, color: 'rgba(0,229,255,0.5)', marginBottom: '4px' },
  bigNum: { fontSize: '38px', fontWeight: 900, fontFamily: 'monospace', color: '#fff', lineHeight: 1.1 },
  kpiVal: { fontSize: '24px', fontWeight: 800, fontFamily: 'monospace', color: CYAN },
  row: { display: 'flex', gap: '20px', flexWrap: 'wrap' as const },
  sectionTitle: { fontSize: '14px', fontWeight: 700, color: '#fff', margin: '0 0 16px 0', display: 'flex' as const, alignItems: 'center', gap: '8px' },
  badge: (color: string) => ({ display: 'inline-block', padding: '3px 10px', borderRadius: '999px', fontSize: '11px', fontWeight: 700, background: color + '22', color, border: `1px solid ${color}55` }),
  th: { color: 'rgba(0,229,255,0.5)', fontWeight: 600, textAlign: 'left' as const, padding: '7px 10px', borderBottom: '1px solid rgba(255,255,255,0.05)', fontSize: '11px', letterSpacing: '0.5px' },
  td: { padding: '9px 10px', borderBottom: '1px solid rgba(255,255,255,0.03)', verticalAlign: 'middle' as const, fontSize: '12px' },
};

/* ═══════════════════════════════════════════════
   KPI Card
   ═══════════════════════════════════════════════ */
function KPICard({ icon, title, value, subtitle, accent = CYAN }: { icon: string; title: string; value: string; subtitle?: string; accent?: string }) {
  return (
    <div style={{ ...S.glass(`${accent}12`), flex: '1', minWidth: '200px', position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', top: -20, right: -20, width: 100, height: 100, borderRadius: '50%', background: `radial-gradient(circle, ${accent}22, transparent 65%)` }} />
      <p style={S.label}>{icon} {title}</p>
      <p style={{ ...S.bigNum, color: accent }}>{value}</p>
      {subtitle && <p style={{ margin: '6px 0 0', fontSize: '11px', color: '#555' }}>{subtitle}</p>}
    </div>
  );
}

/* ═══════════════════════════════════════════════
   Country Heatmap PieChart
   ═══════════════════════════════════════════════ */
function CountryHeatmap({ data }: { data: { dest_currency: string; volume: number; count?: number }[] }) {
  const filtered = useMemo(() => {
    // Map dest_currency to country codes for heatmap
    const currencyToCountry: Record<string, string> = { PEN: 'PERU', COP: 'COLOMBIA', VES: 'VENEZUELA', CLP: 'CHILE', ARS: 'ARGENTINA', MXN: 'MEXICO', USD: 'USA' };
    const aggregated: Record<string, number> = {};
    data.forEach(d => {
      const country = currencyToCountry[d.dest_currency] || d.dest_currency;
      aggregated[country] = (aggregated[country] || 0) + d.volume;
    });
    return Object.entries(aggregated)
      .filter(([c]) => HEATMAP_COUNTRIES.includes(c))
      .sort((a, b) => b[1] - a[1])
      .map(([country, volume], i) => ({ country, volume, color: CHART_COLORS[i % CHART_COLORS.length] }));
  }, [data]);

  const total = filtered.reduce((s, d) => s + d.volume, 0);

  if (!filtered.length) return <p style={{ color: '#333', textAlign: 'center', padding: '20px 0', fontSize: '12px' }}>Sin datos de volumen por país</p>;

  return (
    <div style={{ display: 'flex', gap: '20px', alignItems: 'center', flexWrap: 'wrap' }}>
      <div style={{ width: 160, height: 160, flexShrink: 0 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={filtered.map(d => ({ name: d.country, value: d.volume, color: d.color }))}
              cx="50%" cy="50%" innerRadius={45} outerRadius={75}
              dataKey="value" strokeWidth={0}>
              {filtered.map((entry, i) => <Cell key={i} fill={entry.color} />)}
            </Pie>
            <RechartsTooltip
              contentStyle={{ background: '#111', border: `1px solid ${CYAN}33`, borderRadius: '10px', fontSize: '12px' }}
              formatter={(v: any) => [`$${compact(Number(v))}`, '']}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {filtered.map((d, i) => {
          const pct = total > 0 ? (d.volume / total) * 100 : 0;
          return (
            <div key={d.country}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '4px' }}>
                <span style={{ fontWeight: 600 }}>{COUNTRY_FLAG[d.country] || '🌍'} {d.country}</span>
                <span style={{ color: d.color, fontWeight: 700 }}>{usd(d.volume)} <span style={{ color: '#444' }}>({pct.toFixed(0)}%)</span></span>
              </div>
              <div style={{ height: '5px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${pct}%`, background: d.color, borderRadius: '3px', transition: 'width 1s ease', boxShadow: `0 0 8px ${d.color}88` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════
   Operator Leaderboard
   ═══════════════════════════════════════════════ */
function OperatorLeaderboard({ entries }: { entries: LeaderboardEntry[] }) {
  if (!entries.length) return <p style={{ color: '#333', fontSize: '12px', textAlign: 'center', padding: '20px 0' }}>Sin datos de operadores</p>;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {entries.slice(0, 8).map((e, i) => {
        const isGold = i === 0;
        const medal = RANK_MEDALS[i] || `${i + 1}`;
        const trustColor = e.trust_score >= 90 ? CYAN : e.trust_score >= 75 ? '#f9c74f' : '#43aa8b';
        return (
          <div key={e.alias} style={{
            display: 'flex', alignItems: 'center', gap: '12px',
            padding: '10px 14px', borderRadius: '14px',
            background: isGold ? 'rgba(255,215,0,0.06)' : 'rgba(255,255,255,0.02)',
            border: isGold ? '1px solid rgba(255,215,0,0.3)' : '1px solid rgba(255,255,255,0.04)',
          }}>
            {/* Medal */}
            <div style={{
              width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: isGold ? '20px' : '13px', fontWeight: 800,
              background: isGold ? 'linear-gradient(135deg, #FFD700, #FFA500)' : 'rgba(255,255,255,0.06)',
              color: isGold ? '#000' : '#666',
              boxShadow: isGold ? '0 0 24px rgba(255,215,0,0.5)' : 'none',
              animation: isGold ? 'vipPulse 2s ease-in-out infinite' : 'none',
            }}>{medal}</div>
            {/* Info */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{ margin: 0, fontSize: '13px', fontWeight: 700, color: isGold ? '#FFD700' : '#e0e0e0', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {e.full_name || e.alias}
                {isGold && <span style={{ marginLeft: '8px', fontSize: '10px', color: '#FFD700', letterSpacing: '1px' }}>VIP</span>}
              </p>
              <p style={{ margin: 0, fontSize: '10px', color: '#444' }}>@{e.alias} · {e.orders_month} órdenes</p>
            </div>
            {/* Stats */}
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <p style={{ margin: 0, fontSize: '14px', fontWeight: 800, color: '#00c896' }}>{usd(Number(e.profit_month))}</p>
              <p style={{ margin: 0, fontSize: '10px', color: trustColor, fontWeight: 600 }}>score {e.trust_score}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ═══════════════════════════════════════════════
   Vault Radar (blinking if low)
   ═══════════════════════════════════════════════ */
function VaultRadar() {
  const [vaults, setVaults] = useState<VaultRowData[]>([]);
  useEffect(() => {
    apiRequest('/vaults').then(r => setVaults(r?.vaults || [])).catch(() => { });
  }, []);
  const active = vaults.filter(v => v.is_active);
  if (!active.length) return null;
  const VAULT_COLORS: Record<string, string> = { Digital: PURPLE, Physical: '#43aa8b', Crypto: '#f9c74f' };
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px' }}>
      {active.map(v => {
        const bal = Number(v.balance), thr = Number(v.alert_threshold || '0');
        const isLow = thr > 0 && bal < thr;
        const fillPct = thr > 0 ? Math.min(100, (bal / thr) * 100) : 100;
        const color = VAULT_COLORS[v.vault_type] || CYAN;
        return (
          <div key={v.id} style={{
            flex: '1 1 180px', maxWidth: '240px',
            background: `linear-gradient(135deg, rgba(255,255,255,0.03), ${color}14)`,
            border: isLow ? `1px solid ${color}` : `1px solid ${color}33`,
            borderRadius: '16px', padding: '18px',
            boxShadow: isLow ? `0 0 20px ${color}44, inset 0 0 30px ${color}08` : 'none',
            animation: isLow ? 'vaultBlink 1.4s ease-in-out infinite' : 'none',
          }}>
            <p style={{ ...S.label, color: color + 'aa' }}>
              {v.vault_type === 'Digital' ? '🏦' : v.vault_type === 'Physical' ? '💵' : '₿'} {v.currency}
              {isLow && <span style={{ marginLeft: '6px', color: '#ff6b6b', fontWeight: 900 }}>⚠️</span>}
            </p>
            <p style={{ ...S.bigNum, fontSize: '28px', color: isLow ? '#ff6b6b' : '#fff', margin: '4px 0 2px' }}>
              {compact(bal)}
            </p>
            <p style={{ margin: '0 0 10px', fontSize: '10px', color: '#444', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v.name}</p>
            {thr > 0 && (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#333', marginBottom: '4px' }}>
                  <span>Llenado</span><span>{Math.round(fillPct)}%</span>
                </div>
                <div style={{ height: '5px', background: 'rgba(255,255,255,0.04)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${fillPct}%`, background: isLow ? '#ff6b6b' : color, borderRadius: '3px', transition: 'width 0.8s ease' }} />
                </div>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ═══════════════════════════════════════════════
   Main Admin Dashboard
   ═══════════════════════════════════════════════ */
const COUNTRIES_FILTER = ['', 'CHILE', 'COLOMBIA', 'VENEZUELA', 'PERU', 'ARGENTINA', 'MEXICO', 'USA'];
const COUNTRY_LABEL: Record<string, string> = { '': 'Todos', CHILE: '🇨🇱 Chile', COLOMBIA: '🇨🇴 Colombia', VENEZUELA: '🇻🇪 Venezuela', PERU: '🇵🇪 Perú', ARGENTINA: '🇦🇷 Argentina', MEXICO: '🇲🇽 México', USA: '🇺🇸 USA' };

export default function DashboardPage() {
  const { token } = useAuth();
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [country, setCountry] = useState('');
  const [metrics, setMetrics] = useState<MetricsOverview | null>(null);
  const [companyOverview, setCompanyOverview] = useState<CompanyOverview | null>(null);
  const [alerts, setAlerts] = useState<StuckAlert[]>([]);
  const [profitDaily, setProfitDaily] = useState<ProfitDay[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [statusCounts, setStatusCounts] = useState<{ name: string; value: number; color: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState('');
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchData = useCallback(async (df = dateFrom, dt = dateTo, oc = country) => {
    setLoading(true); setError('');
    try {
      const qp = new URLSearchParams();
      if (df) qp.set('date_from', df);
      if (dt) qp.set('date_to', dt);
      if (oc) qp.set('origin_country', oc);
      const qs = qp.toString() ? `?${qp.toString()}` : '';

      const [metricsData, companyData, alertsData, profitData, lbData] = await Promise.all([
        apiRequest<MetricsOverview>('/metrics/overview'),
        apiRequest<CompanyOverview>(`/metrics/company-overview${qs}`).catch(() => null),
        apiRequest<AlertsResponse>('/alerts/stuck-30m').catch(() => null),
        apiRequest<ProfitDailyResponse>('/metrics/profit_daily?days=7').catch(() => null),
        apiRequest<{ leaderboard: LeaderboardEntry[] }>('/metrics/operator-leaderboard?limit=8').catch(() => null),
      ]);

      setMetrics(metricsData);
      setCompanyOverview(companyData);
      setLeaderboard(lbData?.leaderboard || []);

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
            .map(([name, value]) => ({ name, value: Number(value || 0), color: STATUS_COLORS[name] || '#444' }))
        );
      }
      setLastUpdated(new Date().toLocaleTimeString('es-VE'));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error');
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, country]);

  useEffect(() => { if (token) fetchData(); }, [token, fetchData]);

  const onFilterChange = useCallback((df: string, dt: string, oc: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => fetchData(df, dt, oc), 400);
  }, [fetchData]);

  const handleDateFrom = (v: string) => { setDateFrom(v); onFilterChange(v, dateTo, country); };
  const handleDateTo = (v: string) => { setDateTo(v); onFilterChange(dateFrom, v, country); };
  const handleCountry = (v: string) => { setCountry(v); onFilterChange(dateFrom, dateTo, v); };

  const exportOrders = () => downloadCSV('/metrics/export-orders', `ordenes_${dateFrom || 'all'}.csv`, { date_from: dateFrom, date_to: dateTo, origin_country: country });
  const exportWallets = () => downloadCSV('/origin-wallets/export', `cierres_${dateFrom || 'all'}.csv`, { date_from: dateFrom, date_to: dateTo, origin_country: country });

  const co = companyOverview;
  const volumeUSD = co?.volume?.paid_usd_usdt || 0;
  const profitReal = co?.profit?.total_profit_real_usd || metrics?.total_profit_real_usd || 0;
  const completedOrders = co?.orders?.completed_orders || metrics?.completed_orders || 0;
  const heatmapData = co?.volume?.paid_by_dest_currency || [];

  if (!token) return null;

  return (
    <div style={S.page}>
      {/* Keyframes */}
      <style>{`
        @keyframes vipPulse { 0%,100%{transform:scale(1);box-shadow:0 0 24px rgba(255,215,0,0.5)} 50%{transform:scale(1.1);box-shadow:0 0 40px rgba(255,215,0,0.8)} }
        @keyframes vaultBlink { 0%,100%{border-color:rgba(255,107,107,0.6)} 50%{border-color:rgba(255,107,107,1);box-shadow:0 0 30px rgba(255,107,107,0.4)} }
        @keyframes spin { to{transform:rotate(360deg)} }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: #0a0a0a; }
        ::-webkit-scrollbar-thumb { background: rgba(0,229,255,0.25); border-radius: 3px; }
      `}</style>

      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '28px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={S.h1}>Sendmax Command Center 1.1</h1>
          <p style={{ color: '#333', fontSize: '12px', margin: '4px 0 0' }}>
            Sendmax · Centro de decisiones
            {lastUpdated && <span style={{ color: CYAN + '77', marginLeft: '8px' }}>· {lastUpdated}</span>}
          </p>
        </div>
        <button
          onClick={() => fetchData()}
          disabled={loading}
          style={{
            background: 'none', border: `1px solid ${CYAN}44`, color: CYAN, borderRadius: '12px',
            padding: '8px 18px', cursor: 'pointer', fontSize: '13px', fontWeight: 600,
            transition: 'all 0.2s', opacity: loading ? 0.5 : 1,
          }}
        >
          {loading ? '⟳ Actualizando…' : '⟳ Actualizar'}
        </button>
      </div>

      {error && (
        <div style={{ ...S.glass('rgba(255,50,50,0.1)'), border: '1px solid rgba(255,50,50,0.3)', marginBottom: '20px', color: '#ff6b6b', fontSize: '13px' }}>
          ⚠️ {error}
        </div>
      )}

      {/* ── Filters ── */}
      <div style={{ ...S.glass(), marginBottom: '24px', padding: '16px 20px' }}>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ ...S.label, margin: 0 }}>⚙ Filtros</span>
          {[
            { label: 'Desde', type: 'date', value: dateFrom, onChange: handleDateFrom },
            { label: 'Hasta', type: 'date', value: dateTo, onChange: handleDateTo },
          ].map(f => (
            <div key={f.label} style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <label style={{ ...S.label, fontSize: '9px' }}>{f.label}</label>
              <input type="date" value={f.value}
                onChange={e => f.onChange(e.target.value)}
                style={{ background: 'rgba(255,255,255,0.05)', border: `1px solid ${CYAN}22`, borderRadius: '10px', color: '#e0e0e0', padding: '6px 12px', fontSize: '12px', outline: 'none' }}
              />
            </div>
          ))}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <label style={{ ...S.label, fontSize: '9px' }}>País</label>
            <select value={country} onChange={e => handleCountry(e.target.value)}
              style={{ background: '#0d0d0d', border: `1px solid ${CYAN}22`, borderRadius: '10px', color: '#e0e0e0', padding: '6px 12px', fontSize: '12px', outline: 'none' }}>
              {COUNTRIES_FILTER.map(c => <option key={c} value={c} style={{ background: '#111' }}>{COUNTRY_LABEL[c] || c}</option>)}
            </select>
          </div>
          <div style={{ flex: 1 }} />
          <button onClick={exportOrders} style={{ background: `${CYAN}11`, border: `1px solid ${CYAN}33`, color: CYAN, borderRadius: '10px', padding: '7px 16px', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}>
            ⬇ Órdenes CSV
          </button>
          <button onClick={exportWallets} style={{ background: '#43aa8b11', border: '1px solid #43aa8b44', color: '#43aa8b', borderRadius: '10px', padding: '7px 16px', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}>
            ⬇ Cierres CSV
          </button>
        </div>
      </div>

      {loading && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '12px', padding: '48px 0' }}>
          <div style={{ width: 36, height: 36, border: `3px solid ${CYAN}`, borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
          <span style={{ color: '#444', fontSize: '13px' }}>Cargando datos…</span>
        </div>
      )}

      {metrics && !loading && (
        <>
          {/* ── KPI Row ── */}
          <div style={{ ...S.row, marginBottom: '24px' }}>
            <KPICard icon="📈" title="Volumen Total USD" value={`$${compact(volumeUSD)}`} subtitle={`${(co?.volume?.total_volume_origin || 0) > 0 ? compact(co!.volume.total_volume_origin!) + ' moneda origen' : ''}`} accent={CYAN} />
            <KPICard icon="💰" title="Utilidad Neta Real" value={`$${compact(profitReal)}`} subtitle={`Teórica: $${compact(co?.profit?.total_profit_usd || 0)}`} accent="#00c896" />
            <KPICard icon="📦" title="Órdenes Completadas" value={completedOrders.toLocaleString()} subtitle={`${metrics.pending_orders} pendientes · ${metrics.total_orders} total`} accent={PURPLE} />
            <KPICard icon="🚨" title="Alertas Activas" value={String(alerts.length)} subtitle={alerts.length > 0 ? 'órdenes estancadas +30min' : 'Todo en orden ✓'} accent={alerts.length > 0 ? '#ff6b6b' : '#43aa8b'} />
          </div>

          {/* ── Row: Daily Profit Chart + Status Distribution ── */}
          <div style={{ ...S.row, marginBottom: '24px' }}>
            <div style={{ ...S.glass(), flex: 2, minWidth: 0 }}>
              <p style={S.sectionTitle}>📊 Ganancia Diaria — 7 días</p>
              {profitDaily.length > 0 ? (
                <ResponsiveContainer width="100%" height={240}>
                  <AreaChart data={profitDaily}>
                    <defs>
                      <linearGradient id="gTheo" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#00c896" stopOpacity={0.25} />
                        <stop offset="100%" stopColor="#00c896" stopOpacity={0.01} />
                      </linearGradient>
                      <linearGradient id="gReal" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={CYAN} stopOpacity={0.25} />
                        <stop offset="100%" stopColor={CYAN} stopOpacity={0.01} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
                    <XAxis dataKey="day" tick={{ fontSize: 10, fill: '#444' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: '#444' }} axisLine={false} tickLine={false} tickFormatter={(v: number) => '$' + compact(v)} />
                    <RechartsTooltip
                      contentStyle={{ background: '#111', border: `1px solid ${CYAN}33`, borderRadius: '10px', fontSize: '12px' }}
                      labelStyle={{ color: CYAN }}
                      formatter={(value: any, name: any) => {
                        const n = typeof value === 'number' ? value : Number(value ?? 0);
                        const label = name === 'profit' ? 'Teórico' : 'Neto Real';
                        return ['$' + n.toFixed(2), label];
                      }}
                    />
                    <Area type="monotone" dataKey="profit" stroke="#00c896" strokeWidth={2} fill="url(#gTheo)" dot={false} />
                    <Area type="monotone" dataKey="profit_real" stroke={CYAN} strokeWidth={2} fill="url(#gReal)" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <p style={{ color: '#333', textAlign: 'center', padding: '40px 0', fontSize: '12px' }}>Sin datos de ganancias</p>}
            </div>
            <div style={{ ...S.glass(), flex: 1, minWidth: 260 }}>
              <p style={S.sectionTitle}>🔵 Órdenes por Estado</p>
              {statusCounts.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={140}>
                    <BarChart data={statusCounts} layout="vertical">
                      <XAxis type="number" hide />
                      <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#444' }} axisLine={false} tickLine={false} width={130} />
                      <RechartsTooltip contentStyle={{ background: '#111', border: `1px solid ${CYAN}33`, borderRadius: '10px', fontSize: '12px' }} />
                      <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={16}>
                        {statusCounts.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {statusCounts.map(s => (
                      <div key={s.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <div style={{ width: 8, height: 8, borderRadius: '50%', background: s.color }} />
                          <span style={{ color: '#888' }}>{s.name}</span>
                        </div>
                        <span style={{ fontWeight: 700, color: s.color }}>{s.value}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : <p style={{ color: '#333', textAlign: 'center', padding: '20px 0', fontSize: '12px' }}>Sin datos</p>}
            </div>
          </div>

          {/* ── Row: Country Heatmap + Operator Leaderboard ── */}
          <div style={{ ...S.row, marginBottom: '24px' }}>
            <div style={{ ...S.glass('rgba(0,229,255,0.04)'), flex: 1, minWidth: 280 }}>
              <p style={S.sectionTitle}>🌎 Mapa de Rentabilidad por País</p>
              <CountryHeatmap data={heatmapData} />
            </div>
            <div style={{ ...S.glass('rgba(255,215,0,0.03)'), flex: 1, minWidth: 300, border: '1px solid rgba(255,215,0,0.12)' }}>
              <p style={S.sectionTitle}>🏆 Ranking de Operadores</p>
              <OperatorLeaderboard entries={leaderboard} />
              {leaderboard.length === 0 && <p style={{ color: '#333', fontSize: '11px', textAlign: 'center', marginTop: '4px' }}>Endpoint /metrics/operator-leaderboard no disponible aún</p>}
            </div>
          </div>

          {/* ── Vault Radar ── */}
          <div style={{ ...S.glass(), marginBottom: '24px' }}>
            <p style={S.sectionTitle}>🔐 Radar de Bóvedas</p>
            <VaultRadar />
          </div>

          {/* ── Alerts ── */}
          {alerts.length > 0 && (
            <div style={{ ...S.glass('rgba(255,107,107,0.06)'), border: '1px solid rgba(255,107,107,0.3)', marginBottom: '24px' }}>
              <p style={{ ...S.sectionTitle, color: '#ff6b6b' }}>⚠️ Alertas Activas — {alerts.length} orden{alerts.length > 1 ? 'es' : ''} estancada{alerts.length > 1 ? 's' : ''}</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {alerts.map(a => {
                  const min = Math.floor((Date.now() - new Date(a.updated_at).getTime()) / 60000);
                  return (
                    <div key={a.public_id} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '10px 14px', borderRadius: '12px', background: 'rgba(255,107,107,0.06)', border: '1px solid rgba(255,107,107,0.15)', fontSize: '12px' }}>
                      <span style={{ fontFamily: 'monospace', fontWeight: 700, color: '#ff6b6b' }}>#{a.public_id}</span>
                      <span style={{ ...S.badge('#ff6b6b') }}>{a.status}</span>
                      <span style={{ color: '#666' }}>{COUNTRY_FLAG[a.origin_country] || ''}{a.origin_country} → {COUNTRY_FLAG[a.dest_country] || ''}{a.dest_country}</span>
                      <span style={{ marginLeft: 'auto', color: '#ff6b6b', fontWeight: 700 }}>⏱ {min} min</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ── Footer ── */}
          <div style={{ textAlign: 'center', color: '#1a1a1a', fontSize: '11px', paddingTop: '16px' }}>
            Sendmax Executive Dashboard · {new Date().toLocaleDateString('es-VE')}
          </div>
        </>
      )}
    </div>
  );
}
