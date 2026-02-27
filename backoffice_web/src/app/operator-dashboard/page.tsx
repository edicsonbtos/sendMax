'use client';

/**
 * Operator Dashboard 10x — Dark Tech Premium with Gamification
 * Design: #050505 bg, cyan #00E5FF accents, glassmorphism
 * Features: Trust Score badge, Leaderboard, Wallet card, 24h Activity chart,
 *           Progress bar, Profit by country, Top 5 clients, Orders, Withdrawals
 */

import React, { useState, useEffect, useCallback } from 'react';
import { apiRequest } from '@/lib/api';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Area, AreaChart,
} from 'recharts';

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
interface ProfitByCountry { origin_country: string; total_profit_usdt: string; order_count: number; }
interface TopClient { name: string; order_count: number; total_sent: string; last_order_at: string | null; }
interface Order { public_id: string; origin_country: string; dest_country: string; amount_origin: string; payout_dest: string; profit_usdt: string; status: string; created_at: string; }
interface Withdrawal { id: number; amount_usdt: string; status: string; dest_text: string; country: string; created_at: string; resolved_at: string | null; }
interface LeaderboardEntry {
  alias: string;
  full_name: string;
  trust_score: number;
  profit_month: string;
  orders_month: number;
  kyc_status: string;
  is_me: boolean;
}
interface ActivityHour { hour: string; order_count: number; }
interface DashboardData {
  ok: boolean;
  user: { alias: string; full_name: string; role: string };
  wallet: WalletData;
  monthly_goal: number;
  trust_score: number;
  orders_today: number;
  profit_by_country: ProfitByCountry[];
  top_clients: TopClient[];
  leaderboard: LeaderboardEntry[];
  activity_24h: ActivityHour[];
  recent_orders: Order[];
  withdrawals: Withdrawal[];
  referrals_count: number;
}

/* ═══════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════ */
const usd = (v: string | number) => `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const fmtDate = (iso: string | null) => iso ? new Date(iso).toLocaleString('es-VE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—';
const fmtHour = (iso: string) => { try { return new Date(iso).toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' }); } catch { return iso; } };
const flag: Record<string, string> = { USA: '🇺🇸', CHILE: '🇨🇱', COLOMBIA: '🇨🇴', PERU: '🇵🇪', VENEZUELA: '🇻🇪', MEXICO: '🇲🇽', ARGENTINA: '🇦🇷' };
const STATUS_COLOR: Record<string, string> = { PAGADA: '#00c896', COMPLETADA: '#00c896', EN_PROCESO: '#00b4d8', ORIGEN_VERIFICANDO: '#f9c74f', ORIGEN_CONFIRMADO: '#f9c74f', CREADA: '#888', CANCELADA: '#f44' };
const CHART_COLORS = ['#00E5FF', '#7B2FBE', '#ff6b6b', '#f9c74f', '#43aa8b', '#f8961e'];
const RANK_MEDALS = ['🥇', '🥈', '🥉'];

function trustBadge(score: number): { emoji: string; label: string; color: string } {
  if (score >= 90) return { emoji: '💎', label: 'Élite', color: '#00E5FF' };
  if (score >= 75) return { emoji: '⭐', label: 'Confiable', color: '#f9c74f' };
  if (score >= 50) return { emoji: '🟢', label: 'Estable', color: '#43aa8b' };
  return { emoji: '🔵', label: 'Nuevo', color: '#888' };
}

/* ═══════════════════════════════════════════════════
   Styles
   ═══════════════════════════════════════════════════ */
const S = {
  page: { minHeight: '100vh', background: '#050505', color: '#e0e0e0', fontFamily: "'Inter', 'Segoe UI', sans-serif", padding: '24px', boxSizing: 'border-box' as const },
  glass: (accent = 'rgba(0,229,255,0.08)') => ({
    background: `linear-gradient(135deg, rgba(255,255,255,0.04), ${accent})`,
    backdropFilter: 'blur(16px)',
    border: '1px solid rgba(0,229,255,0.15)',
    borderRadius: '16px',
    padding: '20px',
  }),
  h1: { fontSize: '28px', fontWeight: 800, background: 'linear-gradient(135deg, #00E5FF, #7B2FBE)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', margin: 0 },
  label: { fontSize: '11px', fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase' as const, color: 'rgba(0,229,255,0.6)', marginBottom: '4px' },
  bigNum: { fontSize: '36px', fontWeight: 800, fontFamily: 'monospace', color: '#fff', lineHeight: 1.1 },
  kpiVal: { fontSize: '22px', fontWeight: 800, fontFamily: 'monospace', color: '#00E5FF' },
  row: { display: 'flex', gap: '16px', flexWrap: 'wrap' as const },
  flex1: { flex: '1', minWidth: '180px' },
  table: { width: '100%', borderCollapse: 'collapse' as const, fontSize: '12px' },
  th: { color: 'rgba(0,229,255,0.5)', fontWeight: 600, textAlign: 'left' as const, padding: '6px 8px', borderBottom: '1px solid rgba(255,255,255,0.06)', fontSize: '11px' },
  td: { padding: '7px 8px', borderBottom: '1px solid rgba(255,255,255,0.04)', verticalAlign: 'middle' as const },
  badge: (color: string) => ({ display: 'inline-block', padding: '2px 8px', borderRadius: '999px', fontSize: '11px', fontWeight: 700, background: color + '22', color, border: `1px solid ${color}55` }),
  sectionTitle: { fontSize: '14px', fontWeight: 700, color: '#fff', margin: '0 0 12px 0', display: 'flex' as const, alignItems: 'center', gap: '8px' },
  dot: (color: string) => ({ width: 8, height: 8, borderRadius: '50%', background: color, display: 'inline-block', boxShadow: `0 0 8px ${color}` }),
};

/* ═══════════════════════════════════════════════════
   Sub-components
   ═══════════════════════════════════════════════════ */

function GlassCard({ children, style = {} }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <div style={{ ...S.glass(), ...style }}>{children}</div>;
}

function TrustScoreBadge({ score }: { score: number }) {
  const b = trustBadge(score);
  return (
    <div style={{
      ...S.glass('rgba(0,229,255,0.12)'),
      display: 'flex', alignItems: 'center', gap: '12px', padding: '12px 20px',
    }}>
      <div style={{
        width: 56, height: 56, borderRadius: '50%',
        background: `conic-gradient(${b.color} ${score}%, rgba(255,255,255,0.06) 0)`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{
          width: 44, height: 44, borderRadius: '50%', background: '#0a0a0a',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '20px', fontWeight: 800, color: b.color,
        }}>
          {score}
        </div>
      </div>
      <div>
        <p style={{ margin: 0, fontSize: '12px', color: '#888' }}>Trust Score</p>
        <p style={{ margin: 0, fontSize: '16px', fontWeight: 800, color: b.color }}>
          {b.emoji} {b.label}
        </p>
      </div>
    </div>
  );
}

function LeaderboardTable({ entries }: { entries: LeaderboardEntry[] }) {
  if (!entries.length) return <p style={{ color: '#555', textAlign: 'center', padding: '16px 0' }}>Sin datos</p>;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      {entries.map((e, i) => {
        const isGold = i === 0;
        const medal = RANK_MEDALS[i] || `${i + 1}`;
        return (
          <div key={e.alias} style={{
            display: 'flex', alignItems: 'center', gap: '10px',
            padding: '8px 12px', borderRadius: '12px',
            background: e.is_me ? 'rgba(0,229,255,0.08)' : 'transparent',
            border: e.is_me ? '1px solid rgba(0,229,255,0.25)' : '1px solid transparent',
            transition: 'background 0.2s',
          }}>
            <div style={{
              width: 32, height: 32, borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: isGold ? '20px' : '14px', fontWeight: 800,
              background: isGold ? 'linear-gradient(135deg, #FFD700, #FFA500)' : 'rgba(255,255,255,0.05)',
              color: isGold ? '#000' : '#888',
              animation: isGold ? 'pulse 2s infinite' : 'none',
              boxShadow: isGold ? '0 0 20px rgba(255,215,0,0.4)' : 'none',
            }}>{medal}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{
                margin: 0, fontSize: '13px', fontWeight: e.is_me ? 800 : 600,
                color: e.is_me ? '#00E5FF' : '#e0e0e0',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {e.full_name} {e.is_me && '← Tú'}
                {e.kyc_status === 'APPROVED' && e.trust_score < 90 ? '' : ''}
              </p>
              <p style={{ margin: 0, fontSize: '10px', color: '#555' }}>
                @{e.alias} · {e.orders_month} órdenes · {usd(e.profit_month)}
              </p>
            </div>
            <div style={{ textAlign: 'right' }}>
              <p style={{
                margin: 0, fontSize: '16px', fontWeight: 800,
                color: trustBadge(e.trust_score).color,
              }}>{e.trust_score}</p>
              <p style={{ margin: 0, fontSize: '9px', color: '#555' }}>score</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Activity24hChart({ data }: { data: ActivityHour[] }) {
  const chartData = data.map(d => ({ name: fmtHour(d.hour), orders: d.order_count }));
  if (!chartData.length) return <p style={{ color: '#555', textAlign: 'center', padding: '20px 0' }}>Sin actividad en 24h</p>;
  return (
    <ResponsiveContainer width="100%" height={160}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="cyanGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#00E5FF" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#00E5FF" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
        <XAxis dataKey="name" stroke="#555" fontSize={10} />
        <YAxis stroke="#555" fontSize={10} allowDecimals={false} />
        <RechartsTooltip
          contentStyle={{ background: '#111', border: '1px solid #333', borderRadius: '8px', fontSize: '12px' }}
          labelStyle={{ color: '#00E5FF' }}
        />
        <Area type="monotone" dataKey="orders" stroke="#00E5FF" strokeWidth={2} fill="url(#cyanGrad)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function MiniBarChart({ data }: { data: ProfitByCountry[] }) {
  if (!data.length) return <p style={{ color: '#555', textAlign: 'center', padding: '16px 0' }}>Sin datos</p>;
  const max = Math.max(...data.map(d => Number(d.total_profit_usdt)));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {data.map((d, i) => {
        const pct = max > 0 ? (Number(d.total_profit_usdt) / max) * 100 : 0;
        return (
          <div key={d.origin_country}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '3px' }}>
              <span>{flag[d.origin_country] || '🌍'} {d.origin_country} <span style={{ color: '#555' }}>({d.order_count})</span></span>
              <span style={{ color: '#00E5FF', fontWeight: 700 }}>{usd(d.total_profit_usdt)}</span>
            </div>
            <div style={{ height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${pct}%`, background: `linear-gradient(90deg, ${CHART_COLORS[i % CHART_COLORS.length]}, ${CHART_COLORS[(i + 1) % CHART_COLORS.length]})`, borderRadius: '3px', transition: 'width 0.8s ease' }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ProgressRing({ pct }: { pct: number }) {
  const r = 42, circ = 2 * Math.PI * r;
  const dash = (Math.min(pct, 100) / 100) * circ;
  return (
    <svg width="100" height="100" viewBox="0 0 100 100">
      <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10" />
      <circle cx="50" cy="50" r={r} fill="none" stroke="url(#gradRing)" strokeWidth="10"
        strokeDasharray={`${dash} ${circ - dash}`} strokeDashoffset={circ / 4} strokeLinecap="round"
        style={{ transition: 'stroke-dasharray 1s ease' }} />
      <defs>
        <linearGradient id="gradRing" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#00E5FF" />
          <stop offset="100%" stopColor="#7B2FBE" />
        </linearGradient>
      </defs>
      <text x="50" y="54" textAnchor="middle" fontSize="16" fontWeight="800" fill="#fff">{Math.round(pct)}%</text>
    </svg>
  );
}

/* ═══════════════════════════════════════════════════
   Main Page
   ═══════════════════════════════════════════════════ */
export default function OperatorDashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { setData(await apiRequest('/operator/me/dashboard')); }
    catch (e: unknown) { setError(e instanceof Error ? e.message : 'Error cargando dashboard'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return (
    <div style={{ ...S.page, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px' }}>
      <div style={{ width: 48, height: 48, border: '3px solid #00E5FF', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
      <p style={{ color: '#555' }}>Conectando con el servidor…</p>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}} @keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.1)}}`}</style>
    </div>
  );

  if (error) return (
    <div style={{ ...S.page, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ ...S.glass('rgba(255,50,50,0.1)'), textAlign: 'center', padding: '32px' }}>
        <p style={{ color: '#ff6b6b', fontSize: '16px' }}>⚠️ {error}</p>
      </div>
    </div>
  );

  if (!data) return null;
  const { wallet, trust_score, orders_today, profit_by_country, top_clients, leaderboard, activity_24h, recent_orders, withdrawals, referrals_count, user: u, monthly_goal } = data;
  const profitMonthNum = Number(wallet.profit_month);
  const goalPct = monthly_goal > 0 ? (profitMonthNum / monthly_goal) * 100 : 0;
  const tb = trustBadge(trust_score);

  return (
    <div style={S.page}>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}} @keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.08)}}`}</style>

      {/* ── Header ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '28px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h1 style={S.h1}>Operator Panel</h1>
          <p style={{ color: '#555', fontSize: '13px', margin: '4px 0 0' }}>
            {u?.full_name || u?.alias} · {referrals_count} referido{referrals_count !== 1 ? 's' : ''}
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <TrustScoreBadge score={trust_score} />
          <div style={{ ...S.glass(), padding: '8px 16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={S.dot('#00E5FF')} />
            <span style={{ fontSize: '12px', color: '#00E5FF', fontWeight: 600 }}>LIVE</span>
          </div>
        </div>
      </div>

      {/* ── Wallet Card + Today KPIs ── */}
      <div style={{ ...S.glass('rgba(0,229,255,0.12)'), marginBottom: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <p style={S.label}>💰 Saldo disponible</p>
          <p style={{ ...S.bigNum, fontSize: '44px' }}>{usd(wallet.balance_usdt)}</p>
          <p style={{ color: '#555', fontSize: '12px', marginTop: '4px' }}>USDT · Listo para retirar</p>
        </div>
        <div style={{ display: 'flex', gap: '32px', flexWrap: 'wrap' }}>
          <div>
            <p style={S.label}>Ganancias Hoy</p>
            <p style={{ ...S.kpiVal, color: Number(wallet.profit_today) > 0 ? '#00c896' : '#555' }}>{usd(wallet.profit_today)}</p>
          </div>
          <div>
            <p style={S.label}>Órdenes Hoy</p>
            <p style={{ ...S.kpiVal, color: '#7B2FBE' }}>{orders_today}</p>
          </div>
          <div>
            <p style={S.label}>Este Mes</p>
            <p style={S.kpiVal}>{usd(wallet.profit_month)}</p>
          </div>
          <div>
            <p style={S.label}>Total Histórico</p>
            <p style={{ ...S.kpiVal, color: '#7B2FBE' }}>{usd(wallet.profit_total)}</p>
          </div>
        </div>
      </div>

      {/* ── Leaderboard + Activity Chart ── */}
      <div style={{ ...S.row, marginBottom: '20px' }}>
        <GlassCard style={{ flex: '1', minWidth: '300px' }}>
          <p style={S.sectionTitle}>🏆 Ranking de Operadores</p>
          <LeaderboardTable entries={leaderboard} />
        </GlassCard>

        <div style={{ flex: '1', minWidth: '300px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <GlassCard>
            <p style={S.sectionTitle}>📈 Actividad 24h</p>
            <Activity24hChart data={activity_24h} />
          </GlassCard>

          <GlassCard style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
            <p style={S.sectionTitle}>🎯 Meta Mensual</p>
            <ProgressRing pct={goalPct} />
            <p style={{ color: '#aaa', fontSize: '12px', textAlign: 'center' }}>
              {usd(wallet.profit_month)} / {usd(monthly_goal)} USDT
            </p>
            <div style={{ width: '100%', height: '4px', background: 'rgba(255,255,255,0.05)', borderRadius: '2px' }}>
              <div style={{ height: '100%', width: `${Math.min(goalPct, 100)}%`, background: 'linear-gradient(90deg,#00E5FF,#7B2FBE)', borderRadius: '2px' }} />
            </div>
          </GlassCard>
        </div>
      </div>

      {/* ── Profit by Country + Top 5 Clients ── */}
      <div style={{ ...S.row, marginBottom: '20px' }}>
        <GlassCard style={{ flex: '1', minWidth: '260px' }}>
          <p style={S.sectionTitle}>🌎 Ganancias por País</p>
          <MiniBarChart data={profit_by_country} />
        </GlassCard>

        <GlassCard style={{ flex: '1', minWidth: '260px' }}>
          <p style={S.sectionTitle}>👤 Top 5 Clientes Frecuentes</p>
          {top_clients.length === 0 ? (
            <p style={{ color: '#555', fontSize: '12px', textAlign: 'center', padding: '20px 0' }}>Sin órdenes pagadas aún</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {top_clients.map((c, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ width: '24px', height: '24px', borderRadius: '50%', background: `${CHART_COLORS[i]}22`, border: `1px solid ${CHART_COLORS[i]}55`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '11px', fontWeight: 800, color: CHART_COLORS[i] }}>
                    {i + 1}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ margin: 0, fontSize: '12px', color: '#e0e0e0', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.name}</p>
                    <p style={{ margin: 0, fontSize: '10px', color: '#555' }}>{c.order_count} órdenes · {usd(c.total_sent)} enviado</p>
                  </div>
                  <span style={{ fontSize: '10px', color: '#555' }}>{fmtDate(c.last_order_at)}</span>
                </div>
              ))}
            </div>
          )}
        </GlassCard>
      </div>

      {/* ── Recent Orders ── */}
      <GlassCard style={{ marginBottom: '16px', padding: '0' }}>
        <div style={{ padding: '16px 20px 8px' }}>
          <p style={S.sectionTitle}>📋 Últimas Órdenes</p>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={S.table}>
            <thead>
              <tr>
                {['ID', 'Ruta', 'Enviado', 'Profit', 'Estado', 'Fecha'].map(h => <th key={h} style={S.th}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {recent_orders.slice(0, 10).map(o => (
                <tr key={o.public_id} style={{ transition: 'background 0.2s' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,229,255,0.04)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                  <td style={{ ...S.td, color: '#7B2FBE', fontFamily: 'monospace', fontWeight: 700 }}>#{o.public_id}</td>
                  <td style={{ ...S.td, color: '#e0e0e0' }}>{flag[o.origin_country] || '🌍'}→{flag[o.dest_country] || '🌍'}</td>
                  <td style={{ ...S.td, color: '#aaa' }}>{Number(o.amount_origin).toLocaleString()}</td>
                  <td style={{ ...S.td, color: '#00c896', fontWeight: 700 }}>{o.profit_usdt ? usd(o.profit_usdt) : '—'}</td>
                  <td style={S.td}><span style={S.badge(STATUS_COLOR[o.status] || '#888')}>{o.status.replace('_', ' ')}</span></td>
                  <td style={{ ...S.td, color: '#555', fontSize: '11px' }}>{fmtDate(o.created_at)}</td>
                </tr>
              ))}
              {recent_orders.length === 0 && (
                <tr><td colSpan={6} style={{ ...S.td, textAlign: 'center', color: '#444', padding: '24px' }}>Sin órdenes registradas</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {/* ── Withdrawals ── */}
      <GlassCard style={{ padding: '0' }}>
        <div style={{ padding: '16px 20px 8px' }}>
          <p style={S.sectionTitle}>💸 Historial de Retiros</p>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={S.table}>
            <thead>
              <tr>
                {['Monto', 'Destino', 'País', 'Estado', 'Solicitado', 'Resuelto'].map(h => <th key={h} style={S.th}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {withdrawals.map(w => (
                <tr key={w.id}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,229,255,0.04)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                  <td style={{ ...S.td, color: '#f9c74f', fontWeight: 700 }}>{usd(w.amount_usdt)}</td>
                  <td style={{ ...S.td, color: '#aaa', maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{w.dest_text || '—'}</td>
                  <td style={{ ...S.td, color: '#aaa' }}>{flag[w.country] || ''} {w.country}</td>
                  <td style={S.td}><span style={S.badge(w.status === 'APROBADO' ? '#00c896' : w.status === 'RECHAZADO' ? '#ff6b6b' : '#f9c74f')}>{w.status}</span></td>
                  <td style={{ ...S.td, color: '#555', fontSize: '11px' }}>{fmtDate(w.created_at)}</td>
                  <td style={{ ...S.td, color: w.resolved_at ? '#00c896' : '#444', fontSize: '11px' }}>{fmtDate(w.resolved_at)}</td>
                </tr>
              ))}
              {withdrawals.length === 0 && (
                <tr><td colSpan={6} style={{ ...S.td, textAlign: 'center', color: '#444', padding: '24px' }}>Sin retiros registrados</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </GlassCard>

      {/* ── Footer ── */}
      <div style={{ textAlign: 'center', marginTop: '24px', color: '#282828', fontSize: '11px' }}>
        Sendmax Operator Panel · {new Date().toLocaleDateString('es-VE')}
      </div>
    </div>
  );
}
