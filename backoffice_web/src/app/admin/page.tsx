'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer,
  PieChart, Pie, Cell, BarChart, Bar,
} from 'recharts';
import api from '@/lib/api';
import { useAuth } from '@/components/AuthProvider';
import { cn } from '@/lib/cn';
import { formatCurrency, formatNumber } from '@/lib/formatters';
import type { RealtimeMetrics, VaultBalance } from '@/types';
import SectionHeader from '@/components/ui/SectionHeader';
import MetricCard from '@/components/ui/MetricCard';
import StatCard from '@/components/ui/StatCard';
import MoneyCell from '@/components/ui/MoneyCell';
import FilterBar from '@/components/ui/FilterBar';
import Input from '@/components/ui/Input';
import Button from '@/components/ui/Button';
import LoadingState from '@/components/ui/LoadingState';
import AuditFeed from '@/components/ui/AuditFeed';
import { 
  DollarSign, 
  TrendingUp, 
  CheckCircle2, 
  AlertTriangle, 
  Download, 
  Filter, 
  RefreshCcw, 
  ShieldAlert, 
  LineChart, 
  Users, 
  BarChart as BarChartIcon 
} from 'lucide-react';

// Types adapted to match previous backend schema
interface CompanyOverview {
  ok: boolean;
  orders: { total_orders: number; pending_orders: number; completed_orders: number };
  profit: { total_profit_usd: number; total_profit_real_usd?: number };
  volume: {
    paid_usd_usdt: number;
    total_volume_origin?: number;
    paid_by_dest_currency: { dest_currency: string; volume: number; count?: number }[];
  };
}

interface MetricsOverview {
  total_orders: number; pending_orders: number; completed_orders: number;
  total_volume_usd: number; total_profit_usd: number; total_profit_real_usd?: number;
  status_counts: Record<string, number>;
}

interface StuckAlert { public_id: number; origin_country: string; dest_country: string; status: string; created_at: string; updated_at: string }
interface AlertsResponse { ok: boolean; cutoff_utc: string; origin_verificando_stuck: StuckAlert[]; awaiting_paid_proof_stuck: StuckAlert[] }
interface ProfitDayRaw { day: string; total_orders: number; total_profit: number; total_profit_real?: number; total_volume: number }
interface ProfitDailyResponse { days: number; profit_by_day: ProfitDayRaw[] }
interface ProfitDay { day: string; profit: number; profit_real: number; orders: number; volume: number }
interface VaultRowData { id: number; name: string; vault_type: string; currency: string; balance: string; alert_threshold: string; is_active: boolean }
interface LeaderboardEntry { alias: string; full_name: string; trust_score: number; profit_month: string; orders_month: number; kyc_status: string; }

/* Constantes UI */
const COUNTRY_FLAG: Record<string, string> = {
  PERU: '🇵🇪', COLOMBIA: '🇨🇴', VENEZUELA: '🇻🇪', CHILE: '🇨🇱',
  ARGENTINA: '🇦🇷', MEXICO: '🇲🇽', USA: '🇺🇸', BRASIL: '🇧🇷',
};
const HEATMAP_COUNTRIES = ['PERU', 'COLOMBIA', 'VENEZUELA', 'CHILE', 'ARGENTINA', 'MEXICO'];
const CYAN = '#06b6d4';
const PURPLE = '#8b5cf6';
const CHART_COLORS = [CYAN, PURPLE, '#f59e0b', '#10b981', '#f97316', '#ef4444'];
const COUNTRIES_FILTER = ['', 'CHILE', 'COLOMBIA', 'VENEZUELA', 'PERU', 'ARGENTINA', 'MEXICO', 'USA'];
const COUNTRY_LABEL: Record<string, string> = { '': 'Todos', CHILE: '🇨🇱 Chile', COLOMBIA: '🇨🇴 Colombia', VENEZUELA: '🇻🇪 Venezuela', PERU: '🇵🇪 Peru', ARGENTINA: '🇦🇷 Argentina', MEXICO: '🇲🇽 Mexico', USA: '🇺🇸 USA' };

const STATUS_COLORS: Record<string, string> = {
  PAGADA: '#10b981', CANCELADA: '#ef4444', CREADA: '#f59e0b',
  EN_PROCESO: CYAN, ORIGEN_VERIFICANDO: PURPLE, COMPLETADA: '#10b981',
};

const compact = (n: number) => {
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toFixed(2);
};

/* -----------------------------------------------
   Components locales
----------------------------------------------- */

function OperatorLeaderboard({ entries }: { entries: LeaderboardEntry[] }) {
  if (!entries.length) return <p className="text-gray-500 text-xs text-center py-8">Sin datos de operadores</p>;
  return (
    <div className="flex flex-col gap-2">
      {entries.slice(0, 8).map((e, i) => {
        const isGold = i === 0;
        const medal = i === 0 ? '👑' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`;
        const trustColor = e.trust_score >= 90 ? "text-cyan-400" : e.trust_score >= 75 ? "text-yellow-400" : "text-green-400";

        return (
          <div key={e.alias} className={cn(
            "flex items-center gap-3 p-3 rounded-xl transition-all",
            isGold ? "bg-[#eab30814] border border-[#eab3084d]" : "bg-white/5 border border-white/5 hover:bg-white/10"
          )}>
            <div className={cn(
              "w-9 h-9 rounded-full shrink-0 flex items-center justify-center font-bold text-sm",
              isGold ? "bg-gradient-to-br from-yellow-300 to-yellow-600 shadow-[0_0_15px_rgba(234,179,8,0.4)] text-black" : "bg-white/10 text-gray-400"
            )}>
              {medal}
            </div>
            <div className="flex-1 min-w-0">
              <p className={cn("m-0 text-sm font-bold truncate", isGold ? "text-yellow-400" : "text-gray-200")}>
                {e.full_name || e.alias}
              </p>
              <p className="m-0 text-[10px] text-gray-500 mt-0.5">@{e.alias} • {e.orders_month} órdenes</p>
            </div>
            <div className="text-right shrink-0">
              <p className="m-0 text-sm font-bold text-emerald-400">{formatCurrency(Number(e.profit_month))}</p>
              <p className={cn("m-0 text-[10px] font-bold mt-0.5", trustColor)}>score {e.trust_score}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function CountryHeatmap({ data }: { data: { dest_currency: string; volume: number }[] }) {
  const filtered = useMemo(() => {
    const currencyToCountry: Record<string, string> = { PEN: 'PERU', COP: 'COLOMBIA', VES: 'VENEZUELA', CLP: 'CHILE', ARS: 'ARGENTINA', MXN: 'MEXICO', USD: 'USA' };
    const aggregated: Record<string, number> = {};
    if (Array.isArray(data)) {
      data.forEach(d => {
        const country = currencyToCountry[d.dest_currency] || d.dest_currency;
        aggregated[country] = (aggregated[country] || 0) + d.volume;
      });
    }
    return Object.entries(aggregated)
      .filter(([c]) => HEATMAP_COUNTRIES.includes(c))
      .sort((a, b) => b[1] - a[1])
      .map(([country, volume], i) => ({ country, volume, color: CHART_COLORS[i % CHART_COLORS.length] }));
  }, [data]);

  const total = filtered.reduce((s, d) => s + d.volume, 0);

  if (!filtered.length) return <p className="text-gray-500 text-xs text-center py-8">Sin datos de volumen</p>;

  return (
    <div className="flex gap-6 items-center flex-wrap">
      <div className="w-40 h-40 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={filtered.map(d => ({ name: d.country, value: d.volume, color: d.color }))}
              cx="50%" cy="50%" innerRadius={50} outerRadius={75}
              dataKey="value" strokeWidth={0}>
              {filtered.map((entry, i) => <Cell key={i} fill={entry.color} />)}
            </Pie>
            <RechartsTooltip
              contentStyle={{ background: '#0a0f1e', border: `1px solid ${CYAN}33`, borderRadius: '12px', fontSize: '12px' }}
              itemStyle={{ color: '#fff' }}
              formatter={(v: any) => [`$${compact(Number(v))}`, '']}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="flex-1 flex flex-col gap-3">
        {filtered.map((d) => {
          const pct = total > 0 ? (d.volume / total) * 100 : 0;
          return (
            <div key={d.country}>
              <div className="flex justify-between text-[11px] mb-1">
                <span className="font-semibold text-gray-300">
                  <span className="mr-1">{COUNTRY_FLAG[d.country] || '🌍'}</span> {d.country}
                </span>
                <span style={{ color: d.color }} className="font-bold">
                  {formatCurrency(d.volume)} <span className="text-gray-500 font-medium ml-1">({pct.toFixed(0)}%)</span>
                </span>
              </div>
              <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all duration-1000 ease-out"
                  style={{ width: `${pct}%`, backgroundColor: d.color, boxShadow: `0 0 10px ${d.color}88` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function VaultRadar({ internalVaultAmount }: { internalVaultAmount: number }) {
  const [vaults, setVaults] = useState<VaultRowData[]>([]);

  useEffect(() => {
    api.get<{ vaults: VaultRowData[] }>('/api/vaults').then(res => {
      setVaults(Array.isArray(res.data?.vaults) ? res.data.vaults : []);
    }).catch(() => { });
  }, []);

  const active = vaults.filter(v => v.is_active);
  const VAULT_COLORS: Record<string, string> = { Digital: PURPLE, Physical: '#10b981', Crypto: '#f59e0b', Central: '#ef4444' };

  return (
    <div className="flex flex-wrap gap-4">
      {/* Central Super Vault Injectada vía Backend Lógica Especial */}
      <div className={cn(
        "flex-1 min-w-[200px] max-w-[300px] rounded-2xl p-5 border",
        "bg-gradient-to-br from-[#ef444414] to-[#0a0f1e]",
        "border-[#ef44444d] shadow-[0_0_30px_rgba(239,68,68,0.1),inset_0_0_20px_rgba(239,68,68,0.05)]"
      )}>
        <p className="text-[10px] font-bold tracking-[0.2em] uppercase text-[#ef4444] mb-2 flex items-center gap-2">
          <ShieldAlert size={14} /> BÓVEDA CENTRAL (LÍQUIDA)
        </p>
        <p className="text-3xl font-black font-mono text-white mb-1 shadow-[#ef4444]">
          {compact(internalVaultAmount)} <span className="text-lg text-[#ef4444]">USDT</span>
        </p>
        <p className="text-xs text-red-300/80 font-medium">Net Profit - Operator Withdrawals</p>
      </div>

      {active.map(v => {
        const bal = Number(v.balance), thr = Number(v.alert_threshold || '0');
        const isLow = thr > 0 && bal < thr;
        const fillPct = thr > 0 ? Math.min(100, (bal / thr) * 100) : 100;
        const color = VAULT_COLORS[v.vault_type] || CYAN;

        return (
          <div key={v.id} className={cn(
            "flex-1 min-w-[150px] max-w-[240px] rounded-2xl p-5 border transition-all",
            isLow ? "animate-pulse-glow border-red-500/60 bg-red-500/5" : "border-white/10 bg-white/5"
          )}>
            <p className="text-[10px] font-bold tracking-[0.2em] uppercase mb-2 flex items-center justify-between" style={{ color: color }}>
              <span>[{v.vault_type[0]}] {v.currency}</span>
              {isLow && <span className="text-red-500 text-sm font-black animate-bounce">!</span>}
            </p>
            <p className={cn("text-2xl font-black font-mono mb-1", isLow ? "text-red-400" : "text-white")}>
              {compact(bal)}
            </p>
            <p className="text-[10px] text-gray-500 truncate mb-3">{v.name}</p>
            {thr > 0 && (
              <>
                <div className="flex justify-between text-[9px] text-gray-500 mb-1 font-bold">
                  <span>LLENADO</span><span>{Math.round(fillPct)}%</span>
                </div>
                <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-700" style={{ width: `${fillPct}%`, backgroundColor: isLow ? '#ef4444' : color }} />
                </div>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* -----------------------------------------------
   Page
----------------------------------------------- */
export default function DashboardPage() {
  const { token, role } = useAuth();
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [country, setCountry] = useState('');

  const [metrics, setMetrics] = useState<MetricsOverview | null>(null);
  const [companyOverview, setCompanyOverview] = useState<CompanyOverview | null>(null);
  const [alerts, setAlerts] = useState<StuckAlert[]>([]);
  const [profitDaily, setProfitDaily] = useState<ProfitDay[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [statusCounts, setStatusCounts] = useState<{ name: string; value: number; color: string }[]>([]);
  const [vaultData, setVaultData] = useState<VaultBalance | null>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState('');
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const fetchData = useCallback(async (df = dateFrom, dt = dateTo, oc = country) => {
    setLoading(true); setError('');
    try {
      const qp = new URLSearchParams();
      if (df) qp.set('date_from', df);
      if (dt) qp.set('date_to', dt);
      if (oc) qp.set('origin_country', oc);
      const qs = qp.toString() ? `?${qp.toString()}` : '';

      // Central Vault es traída desde el nuevo api.ts de manera concurrente
      const [mtx, comp, alrt, profit, lb, vaultResponse] = await Promise.allSettled([
        api.get<MetricsOverview>('/metrics/overview'),
        api.get<CompanyOverview>(`/metrics/company-overview${qs}`),
        api.get<AlertsResponse>('/alerts/stuck-30m'),
        api.get<ProfitDailyResponse>('/metrics/profit_daily?days=7'),
        api.get<{ leaderboard: LeaderboardEntry[] }>('/metrics/operator-leaderboard?limit=8'),
        api.get<VaultBalance>('/admin/metrics/vault').catch(() => null)
      ]);

      if (mtx.status === 'fulfilled') setMetrics(mtx.value.data);
      if (comp.status === 'fulfilled') setCompanyOverview(comp.value.data);
      if (lb.status === 'fulfilled') setLeaderboard(Array.isArray(lb.value.data.leaderboard) ? lb.value.data.leaderboard : []);
      if (vaultResponse.status === 'fulfilled' && vaultResponse.value) {
        setVaultData(vaultResponse.value.data);
      }

      const allAlerts: StuckAlert[] = [];
      if (alrt.status === 'fulfilled') {
        const d = alrt.value.data;
        if (Array.isArray(d.origin_verificando_stuck)) allAlerts.push(...d.origin_verificando_stuck);
        if (Array.isArray(d.awaiting_paid_proof_stuck)) allAlerts.push(...d.awaiting_paid_proof_stuck);
      }
      setAlerts(allAlerts);

      if (profit.status === 'fulfilled' && Array.isArray(profit.value.data.profit_by_day)) {
        setProfitDaily(profit.value.data.profit_by_day.map(d => ({
          day: new Date(d.day).toLocaleDateString('es-VE', { weekday: 'short', day: 'numeric' }),
          profit: d.total_profit || 0,
          profit_real: d.total_profit_real || 0,
          orders: d.total_orders || 0,
          volume: d.total_volume || 0,
        })));
      }

      if (mtx.status === 'fulfilled' && mtx.value.data.status_counts) {
        setStatusCounts(
          Object.entries(mtx.value.data.status_counts)
            .filter(([, v]) => (v || 0) > 0)
            .map(([name, value]) => ({ name, value: Number(value || 0), color: STATUS_COLORS[name] || '#888' }))
        );
      }
      setLastUpdated(new Date().toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Error updating dashboard');
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo, country]);

  useEffect(() => { if (token) fetchData(); }, [token, fetchData]);

  const onFilterChange = useCallback((df: string, dt: string, oc: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => fetchData(df, dt, oc), 500);
  }, [fetchData]);

  if (!token) return null;

  const volumeUSD = companyOverview?.volume?.paid_usd_usdt || 0;
  // Calculate Profit
  const theoreticalProfit = companyOverview?.profit?.total_profit_usd || 0;
  const realProfit = companyOverview?.profit?.total_profit_real_usd || metrics?.total_profit_real_usd || 0;
  const completedOrders = companyOverview?.orders?.completed_orders || metrics?.completed_orders || 0;
  const heatmapData = companyOverview?.volume?.paid_by_dest_currency || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <SectionHeader
        title="Command Center"
        subtitle={lastUpdated ? `Sincronizado ${lastUpdated}` : "Revisión maestra financiera"}
        rightSlot={
          <Button
            variant="primary"
            icon={<RefreshCcw size={16} className={loading ? "animate-spin" : ""} />}
            onClick={() => fetchData()}
            loading={loading}
          >
            Actualizar
          </Button>
        }
      />

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500 text-sm font-medium flex items-center gap-3">
          <AlertTriangle size={18} /> {error}
        </div>
      )}

      {/* Filters */}
      <FilterBar>
        <div className="flex items-center gap-2 mr-2 text-white/40">
          <Filter size={18} />
          <span className="text-[10px] font-bold uppercase tracking-[0.2em]">Filtros</span>
        </div>

        <div className="w-full lg:w-48">
          <Input 
            type="date" 
            label="Desde"
            value={dateFrom} 
            onChange={e => { setDateFrom(e.target.value); onFilterChange(e.target.value, dateTo, country); }}
          />
        </div>

        <div className="w-full lg:w-48">
          <Input 
            type="date" 
            label="Hasta"
            value={dateTo} 
            onChange={e => { setDateTo(e.target.value); onFilterChange(dateFrom, e.target.value, country); }}
          />
        </div>

        <div className="w-full lg:w-48">
          <div className="flex flex-col gap-2">
            <label className="text-[10px] font-bold text-white/40 uppercase tracking-[0.2em] ml-1">Origen</label>
            <select 
              value={country} 
              onChange={e => { setCountry(e.target.value); onFilterChange(dateFrom, dateTo, e.target.value); }}
              className="bg-white/5 border border-white/10 text-white rounded-xl h-10 px-3 text-sm focus:ring-blue-500/20 outline-none"
            >
              {COUNTRIES_FILTER.map(c => <option key={c} value={c} className="bg-primary-900">{COUNTRY_LABEL[c] || c}</option>)}
            </select>
          </div>
        </div>

        <div className="flex-1 lg:min-w-0" />

        <div className="flex gap-2">
          <Button variant="secondary" icon={<Download size={14} />} size="sm">Órdenes</Button>
          <Button variant="secondary" icon={<Download size={14} />} size="sm">Cierres</Button>
        </div>
      </FilterBar>

      {metrics && (
        <div className="animate-slide-up">
          {/* Main Financial KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
            <MetricCard
              label="Volumen USDT"
              value={<MoneyCell value={volumeUSD} emphasize />}
              icon={<DollarSign size={24} />}
              hint={(companyOverview?.volume?.total_volume_origin || 0) > 0 ? `${compact(companyOverview!.volume.total_volume_origin!)} en la moneda origen` : "Suma total transada"}
            />

            <MetricCard
              label="Profit Neto Real"
              value={<MoneyCell value={realProfit} emphasize />}
              icon={<TrendingUp size={24} />}
              trendDirection="up"
              hint={`Profit Teórico: $${compact(theoreticalProfit)}`}
            />

            <MetricCard
              label="Completadas"
              value={formatNumber(completedOrders)}
              icon={<CheckCircle2 size={24} />}
              trendDirection="neutral"
              hint={`${metrics.pending_orders} pendientes | ${metrics.total_orders} total`}
            />

            <MetricCard
              label="Alertas Activas"
              value={alerts.length.toString()}
              icon={<AlertTriangle size={24} />}
              trendDirection={alerts.length > 0 ? "down" : "neutral"}
              className={alerts.length > 0 ? "border-red-500/20 shadow-red-900/10" : ""}
              hint={alerts.length > 0 ? "Revisar órdenes congeladas" : "Flujo operativo limpio"}
            />
          </div>

          {/* Central Vault Row (NEW 10x Feature) */}
          <div className="mb-6">
            <h2 className="text-lg font-black text-white mb-4 flex items-center gap-3">
              <ShieldAlert className="text-red-500" /> Tesorería y Bóvedas
            </h2>
            {/* The VaultRadar component pulls vaults via /api/vaults and receives the net central vault amount from the new Backend API */}
            <VaultRadar internalVaultAmount={vaultData?.vault_balance || theoreticalProfit} />
          </div>

          {/* Chart Row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            {/* Area Chart 7 days */}
            <div className="card-glass p-5 lg:col-span-2">
              <h2 className="text-sm font-bold text-gray-300 mb-6 uppercase tracking-widest flex items-center gap-2">
                <LineChart size={16} className="text-emerald-400" /> Ganancia Diaria (Últimos 7 días)
              </h2>
              <div className="h-[280px]">
                {profitDaily.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={profitDaily} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorTheo" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="colorReal" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#ffffff0a" vertical={false} />
                      <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 11, fontWeight: 600 }} dy={10} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 11, fontWeight: 600 }} tickFormatter={v => `$${compact(v)}`} />
                      <RechartsTooltip
                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#ffffff1a', borderRadius: '12px', padding: '12px', boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)' }}
                        itemStyle={{ fontWeight: 700 }} labelStyle={{ color: '#94a3b8', marginBottom: '8px', fontWeight: 600, fontSize: '13px' }}
                        formatter={(val: any, name: any) => [`$${Number(val).toFixed(2)}`, name === 'profit' ? 'Teórico' : 'Neto Real']}
                      />
                      <Area type="monotone" dataKey="profit" stroke="#10b981" strokeWidth={3} fillOpacity={1} fill="url(#colorTheo)" activeDot={{ r: 6, strokeWidth: 0, fill: '#10b981' }} />
                      <Area type="monotone" dataKey="profit_real" stroke="#06b6d4" strokeWidth={3} fillOpacity={1} fill="url(#colorReal)" activeDot={{ r: 6, strokeWidth: 0, fill: '#06b6d4' }} />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-full items-center justify-center text-sm font-medium text-gray-500 border border-dashed border-[#ffffff1a] rounded-xl">Sin datos de ingresos de semana.</div>
                )}
              </div>
            </div>

            {/* Status Bars */}
            <div className="card-glass p-5 flex flex-col">
              <h2 className="text-sm font-bold text-gray-300 mb-6 uppercase tracking-widest flex items-center gap-2">
                <BarChartIcon size={16} className="text-purple-400" /> Estado de Órdenes
              </h2>
              {statusCounts.length > 0 ? (
                <>
                  <div className="h-[160px] mb-4">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={statusCounts} layout="vertical" margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                        <XAxis type="number" hide />
                        <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 10, fontWeight: 600 }} width={120} />
                        <RechartsTooltip cursor={{ fill: '#ffffff0a' }} contentStyle={{ backgroundColor: '#0f172a', borderColor: '#ffffff1a', borderRadius: '12px' }} itemStyle={{ fontWeight: 700, color: '#fff' }} formatter={(val: any) => [val, 'Órdenes']} />
                        <Bar dataKey="value" radius={[0, 6, 6, 0]} barSize={16}>
                          {statusCounts.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="flex-1 overflow-y-auto space-y-2 custom-scrollbar pr-2">
                    {statusCounts.map(s => (
                      <div key={s.name} className="flex items-center justify-between text-xs p-2 rounded-lg bg-white/5 border border-white/5 hover:border-white/10 transition-colors">
                        <div className="flex items-center gap-2">
                          <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: s.color, boxShadow: `0 0 8px ${s.color}66` }} />
                          <span className="font-semibold text-gray-300">{s.name}</span>
                        </div>
                        <span className="font-bold text-white tracking-widest">{s.value}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="flex flex-1 items-center justify-center text-sm font-medium text-gray-500 border border-dashed border-[#ffffff1a] rounded-xl">0 órdenes detectadas.</div>
              )}
            </div>
          </div>

          {/* Leaders & Map Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div className="card-glass p-5">
              <h2 className="text-sm font-bold text-gray-300 mb-6 uppercase tracking-widest flex items-center gap-2">
                <AlertTriangle size={16} className="text-cyan-400" /> Rentabilidad por País
              </h2>
              <CountryHeatmap data={heatmapData} />
            </div>

            <div className="card-glass p-5 border-[#eab30833] relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-yellow-500/5 rounded-full blur-3xl" />
              <h2 className="text-sm font-bold text-yellow-400 mb-6 uppercase tracking-widest flex items-center gap-2 relative z-10">
                <Users size={16} className="text-yellow-400" /> Élite de Operadores
              </h2>
              <div className="relative z-10">
                <OperatorLeaderboard entries={leaderboard} />
              </div>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
