'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Box, Typography, Card, CardContent, Stack, Button,
  Alert, CircularProgress, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Chip, Divider,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  AccountBalanceWallet as WalletIcon,
  TrendingUp as ProfitIcon,
  CalendarMonth as MonthIcon,
  People as ReferralsIcon,
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

/* ── tipos ─────────────────────────────────────────────── */

interface UserDetail {
  id: number;
  telegram_user_id: number;
  alias: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  address_short: string | null;
  role: string;
  is_active: boolean;
  sponsor_id: number | null;
  payout_country: string | null;
  payout_method_text: string | null;
  kyc_status: string;
  kyc_submitted_at: string | null;
  kyc_reviewed_at: string | null;
  kyc_review_reason: string | null;
  created_at: string;
  updated_at: string | null;
  balance_usdt: string | null;
}

interface Metrics {
  profit_today: string;
  profit_month: string;
  referrals_month: string;
}

interface LedgerEntry {
  id: number;
  amount_usdt: string;
  type: string;
  ref_order_public_id: number | null;
  memo: string | null;
  created_at: string;
}

interface WithdrawalEntry {
  id: number;
  amount_usdt: string;
  status: string;
  dest_text: string | null;
  country: string | null;
  fiat: string | null;
  fiat_amount: string | null;
  reject_reason: string | null;
  created_at: string;
  resolved_at: string | null;
}

interface OrderEntry {
  public_id: number;
  origin_country: string;
  dest_country: string;
  amount_origin: string;
  payout_dest: string;
  profit_usdt: string | null;
  status: string;
  created_at: string;
}

interface UserDetailResponse {
  user: UserDetail;
  metrics: Metrics;
  ledger: LedgerEntry[];
  withdrawals: WithdrawalEntry[];
  referrals_count: number;
  orders: OrderEntry[];
}

/* ── helpers ────────────────────────────────────────────── */

function formatUsd(value: string | null | undefined): string {
  if (!value) return '$ 0.00';
  const num = parseFloat(value);
  if (isNaN(num)) return '$ 0.00';
  return `$ ${num.toFixed(2)}`;
}

function formatDate(d: string | null | undefined): string {
  if (!d) return '-';
  return new Date(d).toLocaleDateString('es-ES', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

function formatDateTime(d: string | null | undefined): string {
  if (!d) return '-';
  return new Date(d).toLocaleString('es-ES', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

/* ── constantes de UI ───────────────────────────────────── */

const KYC_MAP: Record<string, { color: 'success' | 'warning' | 'error' | 'default'; label: string }> = {
  APPROVED:  { color: 'success', label: 'Aprobado' },
  SUBMITTED: { color: 'warning', label: 'Enviado' },
  REJECTED:  { color: 'error',   label: 'Rechazado' },
  PENDING:   { color: 'default', label: 'Pendiente' },
};

const ORDER_STATUS_COLORS: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
  PAGADA: 'success', EN_PROCESO: 'warning', CANCELADA: 'error', CREADA: 'info',
};

const WD_STATUS_COLORS: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
  RESUELTA: 'success', SOLICITADA: 'warning', RECHAZADA: 'error',
};

const LEDGER_LABELS: Record<string, string> = {
  ORDER_PROFIT: 'Ganancia orden',
  SPONSOR_COMMISSION: 'Comision referido',
  WITHDRAWAL_HOLD: 'Retiro (hold)',
  WITHDRAWAL_HOLD_REVERSAL: 'Retiro revertido',
};

/* ── sub-componentes ────────────────────────────────────── */

type IconComponent = React.ElementType<{ sx?: object }>;

interface StatCardProps {
  title: string;
  value: string;
  Icon: IconComponent;
  color: string;
}

function StatCard({ title, value, Icon, color }: StatCardProps) {
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
          </Box>
          <Box sx={{
            backgroundColor: color + '12',
            borderRadius: '14px', p: 1.25,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Icon sx={{ color, fontSize: 26 }} />
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

function InfoRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <Box sx={{ minWidth: 200, py: 0.5 }}>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.25 }}>
        {label}
      </Typography>
      <Typography variant="body2" sx={{ fontWeight: 500 }}>{value || '-'}</Typography>
    </Box>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <Typography variant="h6" sx={{ fontWeight: 700, mt: 4, mb: 2 }}>
      {children}
    </Typography>
  );
}

function EmptyRow({ cols, text }: { cols: number; text: string }) {
  return (
    <TableRow>
      <TableCell colSpan={cols} align="center" sx={{ py: 4 }}>
        <Typography variant="body2" color="text.secondary">{text}</Typography>
      </TableCell>
    </TableRow>
  );
}

/* ── pagina principal ───────────────────────────────────── */

export default function UserDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { token } = useAuth();

  const userId = params?.id as string;

  const [data, setData] = useState<UserDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchDetail = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    setError('');
    try {
      const res = await apiRequest<UserDetailResponse>(`/users/${userId}`);
      setData(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error cargando usuario');
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    if (token) fetchDetail();
  }, [token, fetchDetail]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 12 }}>
        <CircularProgress sx={{ color: '#4B2E83' }} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 4 }}>
        <Button startIcon={<BackIcon />} onClick={() => router.push('/users')} sx={{ mb: 2 }}>
          Volver a usuarios
        </Button>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!data) return null;

  const { user, metrics, ledger, withdrawals, referrals_count, orders } = data;
  const kycCfg = KYC_MAP[user.kyc_status] ?? KYC_MAP.PENDING;

  return (
    <Box className="fade-in" sx={{ maxWidth: 1200, mx: 'auto' }}>

      {/* ── HEADER ── */}
      <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
        <Button
          startIcon={<BackIcon />}
          onClick={() => router.push('/users')}
          variant="outlined"
          size="small"
        >
          Volver
        </Button>
        <Box sx={{ flex: 1 }}>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>
            {user.full_name || user.alias}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            @{user.alias} &middot; ID #{user.id}
          </Typography>
        </Box>
        <Chip
          label={user.role}
          color={user.role === 'admin' ? 'error' : 'primary'}
          sx={{ fontWeight: 700 }}
        />
        <Chip
          label={user.is_active ? 'Activo' : 'Inactivo'}
          color={user.is_active ? 'success' : 'default'}
        />
        <Chip label={kycCfg.label} color={kycCfg.color} />
      </Stack>

      {/* ── METRICAS ── */}
      <Stack direction="row" flexWrap="wrap" gap={2} sx={{ mb: 3 }}>
        <StatCard title="Balance Wallet" value={formatUsd(user.balance_usdt)} Icon={WalletIcon} color="#4B2E83" />
        <StatCard title="Profit Hoy" value={formatUsd(metrics.profit_today)} Icon={ProfitIcon} color="#16A34A" />
        <StatCard title="Profit Mes" value={formatUsd(metrics.profit_month)} Icon={MonthIcon} color="#2563EB" />
        <StatCard title="Comisiones Referidos" value={formatUsd(metrics.referrals_month)} Icon={ReferralsIcon} color="#D97706" />
      </Stack>

      {/* ── INFO PERSONAL ── */}
      <Card sx={{ mb: 1 }}>
        <CardContent>
          <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Informacion</Typography>
          <Stack direction="row" flexWrap="wrap" gap={2.5}>
            <InfoRow label="Telegram ID" value={
              <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                {user.telegram_user_id || '-'}
              </Typography>
            } />
            <InfoRow label="Email" value={user.email} />
            <InfoRow label="Telefono" value={user.phone} />
            <InfoRow label="Direccion" value={user.address_short} />
            <InfoRow label="Pais pago" value={user.payout_country} />
            <InfoRow label="Metodo pago" value={user.payout_method_text} />
            <InfoRow label="Sponsor" value={user.sponsor_id ? `#${user.sponsor_id}` : '-'} />
            <InfoRow label="Referidos" value={String(referrals_count)} />
            <InfoRow label="Registrado" value={formatDate(user.created_at)} />
            <InfoRow label="Actualizado" value={formatDate(user.updated_at)} />
            <InfoRow label="KYC enviado" value={formatDate(user.kyc_submitted_at)} />
            <InfoRow label="KYC revisado" value={formatDate(user.kyc_reviewed_at)} />
          </Stack>
          {user.kyc_review_reason && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="caption" color="text.secondary">Razon KYC</Typography>
              <Typography variant="body2">{user.kyc_review_reason}</Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      <Divider sx={{ my: 2 }} />

      {/* ── LEDGER ── */}
      <SectionTitle>Movimientos Wallet</SectionTitle>
      <Card>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>Tipo</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="right">Monto USDT</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Ref Orden</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Memo</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Fecha</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {ledger.length === 0 ? (
                <EmptyRow cols={5} text="Sin movimientos" />
              ) : (
                ledger.map((l) => {
                  const amount = parseFloat(l.amount_usdt || '0');
                  const isPositive = amount >= 0;
                  return (
                    <TableRow key={l.id}>
                      <TableCell>
                        <Chip
                          label={LEDGER_LABELS[l.type] ?? l.type}
                          size="small"
                          color={isPositive ? 'success' : 'error'}
                          variant="outlined"
                          sx={{ fontSize: 12 }}
                        />
                      </TableCell>
                      <TableCell align="right" sx={{
                        fontWeight: 600,
                        color: isPositive ? '#16A34A' : '#DC2626',
                      }}>
                        {isPositive ? '+' : ''}{formatUsd(l.amount_usdt)}
                      </TableCell>
                      <TableCell sx={{ fontFamily: 'monospace', fontSize: 13 }}>
                        {l.ref_order_public_id ? `#${l.ref_order_public_id}` : '-'}
                      </TableCell>
                      <TableCell sx={{
                        maxWidth: 200, overflow: 'hidden',
                        textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                      }}>
                        {l.memo || '-'}
                      </TableCell>
                      <TableCell>{formatDateTime(l.created_at)}</TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* ── RETIROS ── */}
      <SectionTitle>Retiros</SectionTitle>
      <Card>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>#</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="right">Monto USDT</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Destino</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Pais / Fiat</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Fecha</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {withdrawals.length === 0 ? (
                <EmptyRow cols={6} text="Sin retiros" />
              ) : (
                withdrawals.map((w) => (
                  <TableRow key={w.id}>
                    <TableCell>{w.id}</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>
                      {formatUsd(w.amount_usdt)}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={w.status}
                        size="small"
                        color={WD_STATUS_COLORS[w.status] ?? 'default'}
                        sx={{ fontWeight: 600, fontSize: 12 }}
                      />
                    </TableCell>
                    <TableCell sx={{
                      maxWidth: 180, overflow: 'hidden',
                      textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {w.dest_text || '-'}
                    </TableCell>
                    <TableCell>
                      {[w.country, w.fiat].filter(Boolean).join(' / ') || '-'}
                      {w.fiat_amount ? ` (${parseFloat(w.fiat_amount).toFixed(0)})` : ''}
                    </TableCell>
                    <TableCell>{formatDateTime(w.created_at)}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>

      {/* ── ORDENES ── */}
      <SectionTitle>Ordenes Recientes</SectionTitle>
      <Card sx={{ mb: 4 }}>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 700 }}>ID</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Ruta</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="right">Monto</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="right">Pago</TableCell>
                <TableCell sx={{ fontWeight: 700 }} align="right">Profit</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Fecha</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {orders.length === 0 ? (
                <EmptyRow cols={7} text="Sin ordenes" />
              ) : (
                orders.map((o) => (
                  <TableRow key={o.public_id}>
                    <TableCell sx={{ fontFamily: 'monospace' }}>#{o.public_id}</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>
                      {o.origin_country} → {o.dest_country}
                    </TableCell>
                    <TableCell align="right">{formatUsd(o.amount_origin)}</TableCell>
                    <TableCell align="right">{formatUsd(o.payout_dest)}</TableCell>
                    <TableCell align="right" sx={{ color: '#16A34A', fontWeight: 600 }}>
                      {formatUsd(o.profit_usdt)}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={o.status}
                        size="small"
                        color={ORDER_STATUS_COLORS[o.status] ?? 'default'}
                        sx={{ fontWeight: 600, fontSize: 12 }}
                      />
                    </TableCell>
                    <TableCell>{formatDateTime(o.created_at)}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Card>
    </Box>
  );
}
