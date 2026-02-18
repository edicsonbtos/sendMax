'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box, Typography, Card, CardContent, Stack, Button, TextField,
  Alert, CircularProgress, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Divider, Chip, Dialog, DialogTitle,
  DialogContent, DialogActions, Snackbar, Avatar, Tooltip,
  Tabs, Tab,
} from '@mui/material';
import {
  Download as DownloadIcon, Lock as LockIcon,
  CheckCircle as CheckIcon, Refresh as RefreshIcon,
  TrendingUp as InIcon, TrendingDown as OutIcon,
  Warning as WarningIcon, Receipt as OrdersIcon,
  AttachMoney as ProfitIcon, HourglassEmpty as PendingIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

/* ================================================================
   INTERFACES — mapeadas 1:1 al backend real (verificado 2026-02-13)
   ================================================================ */


interface BalanceItem {
  origin_country: string;
  fiat_currency: string;
  opening_balance: number;
  in_today: number;
  out_today: number;
  current_balance: number;
}

interface BalancesResponse {
  ok: boolean;
  day: string;
  prev_day: string;
  items: BalanceItem[];
}

interface CloseReportItem {
  origin_country: string;
  fiat_currency: string;
  in_amount: number;
  out_amount: number;
  net_amount: number;
  pending_origin_verificando_count: number;
  ok_to_close: boolean;
  closed: boolean;
  closed_at: string | null;
  closed_by_telegram_id: number | null;
  close_note: string | null;
  net_amount_at_close: number | null;
}

interface CloseReportResponse {
  ok: boolean;
  day: string;
  items: CloseReportItem[];
}

interface DailyCloseResponse {
  ok: boolean;
  day_local: string;
  tz: string;
  window_utc: { start: string; end: string };
  status_counts: {
    creadas: number;
    origen_verificando: number;
    origen_confirmado: number;
    en_proceso: number;
    pagadas: number;
    canceladas: number;
    awaiting_paid_proof: number;
  };
  profit_usdt_paid_window: number;
  volume_by_origin_amount_origin: Array<{
    origin_country: string;
    amount_origin_sum: number;
  }>;
}

interface CloseResultResponse {
  ok: boolean;
  id: number | null;
  net_amount_at_close: number;
}

interface DailyMovement {
  day: string;
  origin_country: string;
  fiat_currency: string;
  amount_fiat: number;
  ref_order_public_id: number | null;
  created_at: string;
  created_by_telegram_id: number | null;
  note: string | null;
  approved_at: string | null;
  approved_by_telegram_id: number | null;
  approved_note: string | null;
}

interface DailyResponse {
  ok: boolean;
  day: string;
  totals: Array<{
    origin_country: string;
    fiat_currency: string;
    total_amount_fiat: number;
    movements: number;
  }>;
  movements: DailyMovement[];
}

interface SweepItem {
  id: number;
  day: string;
  origin_country: string;
  fiat_currency: string;
  amount_fiat: number;
  created_at: string;
  created_by_telegram_id: number | null;
  note: string | null;
  external_ref: string | null;
}

interface SweepsResponse {
  ok: boolean;
  day: string;
  count: number;
  sweeps: SweepItem[];
}

/* ================================================================
   HELPERS
   ================================================================ */

const getCurrencySymbol = (c: string) => {
  const s: Record<string, string> = {
    USD: '$', USDT: '$', COP: 'COL$', PEN: 'S/', VES: 'Bs.',
    CLP: 'CLP$', ARS: 'AR$', BRL: 'R$', MXN: 'MX$', BOB: 'Bs',
    EUR: 'EUR', GBP: 'GBP',
  };
  return s[c] || c;
};

const formatMoney = (amount: number, currency: string) => {
  const decimals = ['COP', 'VES', 'CLP'].includes(currency) ? 0 : 2;
  return amount.toLocaleString('es-VE', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

const formatMoneyCSV = (amount: number, currency: string) => {
  const decimals = ['COP', 'VES', 'CLP'].includes(currency) ? 0 : 2;
  return amount.toFixed(decimals);
};

const sanitizeCSV = (value: string | null | undefined): string => {
  if (!value) return '';
  const s = String(value);
  if (/^[=+\-@\t\r]/.test(s)) return "'" + s;
  if (s.includes(',') || s.includes('"') || s.includes('\n')) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
};

const getCountryInfo = (country: string): { code: string; color: string } => {
  const info: Record<string, { code: string; color: string }> = {
    VENEZUELA: { code: 'VE', color: '#FFCD00' },
    COLOMBIA: { code: 'CO', color: '#FCD116' },
    PERU: { code: 'PE', color: '#D91023' },
    CHILE: { code: 'CL', color: '#0039A6' },
    USA: { code: 'US', color: '#3C3B6E' },
    MEXICO: { code: 'MX', color: '#006847' },
    ARGENTINA: { code: 'AR', color: '#74ACDF' },
    BRASIL: { code: 'BR', color: '#009B3A' },
    ECUADOR: { code: 'EC', color: '#FFD100' },
    BOLIVIA: { code: 'BO', color: '#007934' },
    PANAMA: { code: 'PA', color: '#005293' },
  };
  return info[country?.toUpperCase()] || { code: (country || '??').substring(0, 2), color: '#64748B' };
};

const CountryBadge = ({ country }: { country: string }) => {
  const info = getCountryInfo(country);
  return (
    <Avatar sx={{ width: 28, height: 28, fontSize: '0.7rem', fontWeight: 800, bgcolor: info.color, color: '#fff' }}>
      {info.code}
    </Avatar>
  );
};

const isValidDay = (day: string) => /^\d{4}-\d{2}-\d{2}$/.test(day);

/* ================================================================
   COMPONENT
   ================================================================ */

export default function DailyClosePage() {
  const { token } = useAuth();

  const [selectedDay, setSelectedDay] = useState('');
  const [report, setReport] = useState<CloseReportItem[]>([]);
  const [dailySummary, setDailySummary] = useState<DailyCloseResponse | null>(null);
  const [movements, setMovements] = useState<DailyMovement[]>([]);
  const [sweeps, setSweeps] = useState<SweepItem[]>([]);
  const [balances, setBalances] = useState<BalanceItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState(0);

  const [closeTarget, setCloseTarget] = useState<CloseReportItem | null>(null);
  const [closeNote, setCloseNote] = useState('');
  const [closeLoading, setCloseLoading] = useState(false);
  const [batchMode, setBatchMode] = useState<'safe' | 'force' | null>(null);

  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' | 'info' });

  useEffect(() => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    setSelectedDay(yesterday.toLocaleDateString('en-CA'));
  }, []);

  /* -- Fetch ------------------------------------------------- */
  const fetchData = useCallback(async () => {
    if (!selectedDay || !isValidDay(selectedDay)) return;
    setLoading(true);
    setError('');
    try {
      const [reportData, summaryData, movData, sweepData, balanceData] = await Promise.all([
        apiRequest<CloseReportResponse>('/origin-wallets/close-report?day=' + selectedDay),
        apiRequest<DailyCloseResponse>('/daily-close?day=' + selectedDay),
        apiRequest<DailyResponse>('/origin-wallets/daily?day=' + selectedDay).catch(() => null),
        apiRequest<SweepsResponse>('/origin-wallets/sweeps?day=' + selectedDay).catch(() => null),
        apiRequest<BalancesResponse>('/origin-wallets/balances2?day=' + selectedDay).catch(() => null),
      ]);
      setReport(reportData?.items || []);
      setDailySummary(summaryData || null);
      setMovements(movData?.movements || []);
      setSweeps(sweepData?.sweeps || []);
      setBalances(balanceData?.items || []);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error desconocido';
      setError(message);
      setReport([]);
      setDailySummary(null);
      setMovements([]);
      setSweeps([]);
    } finally {
      setLoading(false);
    }
  }, [selectedDay]);

  useEffect(() => {
    if (selectedDay && token && isValidDay(selectedDay)) fetchData();
  }, [selectedDay, token, fetchData]);

  /* -- Derived ------------------------------------------------ */
  const sc = dailySummary?.status_counts;
  const totalOrders = sc ? sc.creadas + sc.origen_verificando + sc.origen_confirmado + sc.en_proceso + sc.pagadas + sc.canceladas : 0;
  const profitDay = dailySummary?.profit_usdt_paid_window || 0;

  const kpisByCurrency = useMemo(() => {
    const map: Record<string, { currency: string; totalIn: number; totalOut: number; net: number; countries: number }> = {};
    report.forEach((r) => {
      if (!map[r.fiat_currency]) {
        map[r.fiat_currency] = { currency: r.fiat_currency, totalIn: 0, totalOut: 0, net: 0, countries: 0 };
      }
      map[r.fiat_currency].totalIn += r.in_amount || 0;
      map[r.fiat_currency].totalOut += r.out_amount || 0;
      map[r.fiat_currency].net += r.net_amount || 0;
      map[r.fiat_currency].countries += 1;
    });
    return Object.values(map).sort((a, b) => Math.abs(b.net) - Math.abs(a.net));
  }, [report]);

  const closedCount = report.filter((r) => r.closed).length;
  const readyToCloseCount = report.filter((r) => !r.closed && r.ok_to_close).length;
  const notReadyCount = report.filter((r) => !r.closed && !r.ok_to_close).length;
  const pendingVerifCount = report.reduce((sum, r) => sum + (r.pending_origin_verificando_count || 0), 0);
  const allClosed = report.length > 0 && closedCount === report.length;

  /* -- Close per row ------------------------------------------ */
  const handleOpenClose = (item: CloseReportItem) => {
    setCloseTarget(item);
    setCloseNote('');
  };

  const handleConfirmClose = async () => {
    if (!closeTarget) return;
    setCloseLoading(true);
    try {
      const result = await apiRequest<CloseResultResponse>('/origin-wallets/close', {
        method: 'POST',
        body: JSON.stringify({
          day: selectedDay,
          origin_country: closeTarget.origin_country,
          fiat_currency: closeTarget.fiat_currency,
          note: closeNote || null,
        }),
      });
      setSnackbar({
        open: true, severity: 'success',
        message: 'Cerrado ' + closeTarget.origin_country + ' / ' + closeTarget.fiat_currency + ' | Neto: ' + getCurrencySymbol(closeTarget.fiat_currency) + ' ' + formatMoney(result.net_amount_at_close, closeTarget.fiat_currency),
      });
      setCloseTarget(null);
      fetchData();
    } catch (err: unknown) {
      setSnackbar({ open: true, severity: 'error', message: err instanceof Error ? err.message : 'Error al cerrar' });
    } finally {
      setCloseLoading(false);
    }
  };

  /* -- Batch close -------------------------------------------- */
  const handleBatchClose = async (mode: 'safe' | 'force') => {
    const toClose = mode === 'safe'
      ? report.filter((r) => !r.closed && r.ok_to_close)
      : report.filter((r) => !r.closed);
    if (toClose.length === 0) {
      setSnackbar({ open: true, severity: 'info', message: 'No hay billeteras pendientes de cerrar' });
      setBatchMode(null);
      return;
    }
    setCloseLoading(true);
    let ok = 0;
    let fail = 0;
    const batchSize = 4;
    for (let i = 0; i < toClose.length; i += batchSize) {
      const batch = toClose.slice(i, i + batchSize);
      const results = await Promise.allSettled(
        batch.map((item) =>
          apiRequest('/origin-wallets/close', {
            method: 'POST',
            body: JSON.stringify({
              day: selectedDay,
              origin_country: item.origin_country,
              fiat_currency: item.fiat_currency,
              note: mode === 'force' ? 'Cierre forzado masivo desde backoffice' : 'Cierre masivo desde backoffice',
            }),
          })
        )
      );
      results.forEach((r) => { if (r.status === 'fulfilled') ok++; else fail++; });
    }
    setSnackbar({
      open: true,
      severity: fail === 0 ? 'success' : 'error',
      message: 'Cierre masivo: ' + ok + ' cerrados' + (fail > 0 ? ', ' + fail + ' fallidos' : ''),
    });
    setBatchMode(null);
    setCloseLoading(false);
    fetchData();
  };

  /* -- CSV ---------------------------------------------------- */
  const exportCSV = () => {
    if (report.length === 0) return;
    const headers = ['Pais', 'Moneda', 'Saldo_Inicial', 'Entradas', 'Salidas', 'Neto', 'Saldo_Final', 'Pendientes_Verificando', 'OK_Cerrar', 'Cerrado', 'Neto_Al_Cierre', 'Nota_Cierre'];
    const rows = report.map((r) => {
      const bal = balances.find(b => b.origin_country === r.origin_country && b.fiat_currency === r.fiat_currency);
      return [
        sanitizeCSV(r.origin_country),
        sanitizeCSV(r.fiat_currency),
        bal ? formatMoneyCSV(bal.opening_balance, r.fiat_currency) : '0',
        formatMoneyCSV(r.in_amount, r.fiat_currency),
        formatMoneyCSV(r.out_amount, r.fiat_currency),
        formatMoneyCSV(r.net_amount, r.fiat_currency),
        bal ? formatMoneyCSV(bal.current_balance, r.fiat_currency) : '0',
        String(r.pending_origin_verificando_count),
        r.ok_to_close ? 'SI' : 'NO',
        r.closed ? 'SI' : 'NO',
        r.net_amount_at_close != null ? formatMoneyCSV(r.net_amount_at_close, r.fiat_currency) : '',
        sanitizeCSV(r.close_note),
      ];
    });
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'cierre_' + selectedDay + '.csv';
    link.click();
  };

  /* ================================================================
     RENDER
     ================================================================ */
  return (
    <Box className="fade-in">
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>Cierre Diario</Typography>
          <Typography variant="body2" sx={{ color: '#64748B', mt: 0.5 }}>
            Consolidacion de billeteras y ordenes por dia
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" startIcon={<DownloadIcon />} onClick={exportCSV} disabled={report.length === 0} size="small">CSV</Button>
          <Button variant="contained" startIcon={<RefreshIcon />} onClick={fetchData} disabled={loading}>Actualizar</Button>
        </Stack>
      </Stack>

      {/* Date picker */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 2.5 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="center">
            <TextField
              type="date" label="Dia a consultar / cerrar"
              value={selectedDay} onChange={(e) => setSelectedDay(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              sx={{ width: 220 }} size="small"
              error={selectedDay !== '' && !isValidDay(selectedDay)}
              helperText={selectedDay !== '' && !isValidDay(selectedDay) ? 'Formato: YYYY-MM-DD' : ''}
            />
            <Chip label={selectedDay} size="small" sx={{ backgroundColor: '#EFEAFF', color: '#4B2E83', fontWeight: 700 }} />
            {dailySummary && (
              <Chip label={dailySummary.tz} size="small" variant="outlined" sx={{ fontWeight: 600, fontSize: '0.7rem' }} />
            )}
            <Box sx={{ flex: 1 }} />
            {allClosed && <Chip icon={<CheckIcon />} label="DIA COMPLETAMENTE CERRADO" color="success" sx={{ fontWeight: 700 }} />}
          </Stack>
        </CardContent>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress sx={{ color: '#4B2E83' }} />
        </Box>
      ) : (
        <>
          {/* KPI Row 1: Ordenes */}
          {dailySummary && sc && (
            <Card sx={{ mb: 3, p: 2.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#64748B', mb: 2, textTransform: 'uppercase', fontSize: '0.7rem', letterSpacing: 1 }}>
                Resumen de Ordenes del Dia
              </Typography>
              <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap', gap: 2 }}>
                <Card variant="outlined" sx={{ flex: '1 1 160px', minWidth: 140 }}>
                  <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Box>
                        <Typography variant="caption" sx={{ color: '#64748B' }}>Total Ordenes</Typography>
                        <Typography variant="h5" sx={{ fontWeight: 800, color: '#4B2E83' }}>{totalOrders}</Typography>
                      </Box>
                      <OrdersIcon sx={{ color: '#4B2E83', fontSize: 28, opacity: 0.3 }} />
                    </Stack>
                  </CardContent>
                </Card>
                <Card variant="outlined" sx={{ flex: '1 1 160px', minWidth: 140, borderColor: '#16A34A40', backgroundColor: '#F0FDF4' }}>
                  <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Box>
                        <Typography variant="caption" sx={{ color: '#16A34A' }}>Pagadas</Typography>
                        <Typography variant="h5" sx={{ fontWeight: 800, color: '#16A34A' }}>{sc.pagadas}</Typography>
                      </Box>
                      <CheckIcon sx={{ color: '#16A34A', fontSize: 28, opacity: 0.3 }} />
                    </Stack>
                  </CardContent>
                </Card>
                <Card variant="outlined" sx={{ flex: '1 1 160px', minWidth: 140, borderColor: '#2563EB40', backgroundColor: '#EFF6FF' }}>
                  <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Box>
                        <Typography variant="caption" sx={{ color: '#2563EB' }}>Profit USDT</Typography>
                        <Typography variant="h5" sx={{ fontWeight: 800, color: profitDay > 0 ? '#16A34A' : '#94A3B8' }}>
                          {'$' + profitDay.toFixed(2)}
                        </Typography>
                      </Box>
                      <ProfitIcon sx={{ color: '#2563EB', fontSize: 28, opacity: 0.3 }} />
                    </Stack>
                  </CardContent>
                </Card>
                {sc.origen_verificando > 0 && (
                  <Card variant="outlined" sx={{ flex: '1 1 160px', minWidth: 140, borderColor: '#F59E0B40', backgroundColor: '#FFFBEB' }}>
                    <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Box>
                          <Typography variant="caption" sx={{ color: '#F59E0B' }}>Verificando</Typography>
                          <Typography variant="h5" sx={{ fontWeight: 800, color: '#F59E0B' }}>{sc.origen_verificando}</Typography>
                        </Box>
                        <PendingIcon sx={{ color: '#F59E0B', fontSize: 28, opacity: 0.3 }} />
                      </Stack>
                    </CardContent>
                  </Card>
                )}
                {sc.awaiting_paid_proof > 0 && (
                  <Card variant="outlined" sx={{ flex: '1 1 160px', minWidth: 140, borderColor: '#DC262640', backgroundColor: '#FEF2F2' }}>
                    <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center">
                        <Box>
                          <Typography variant="caption" sx={{ color: '#DC2626' }}>Esperan Prueba</Typography>
                          <Typography variant="h5" sx={{ fontWeight: 800, color: '#DC2626' }}>{sc.awaiting_paid_proof}</Typography>
                        </Box>
                        <WarningIcon sx={{ color: '#DC2626', fontSize: 28, opacity: 0.3 }} />
                      </Stack>
                    </CardContent>
                  </Card>
                )}
                <Card variant="outlined" sx={{ flex: '1 1 240px', minWidth: 200 }}>
                  <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                    <Typography variant="caption" sx={{ color: '#64748B', fontWeight: 600 }}>Desglose</Typography>
                    <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap', gap: 0.5 }}>
                      {sc.creadas > 0 && <Chip label={'Creadas: ' + sc.creadas} size="small" color="warning" variant="outlined" />}
                      {sc.origen_confirmado > 0 && <Chip label={'Origen OK: ' + sc.origen_confirmado} size="small" color="info" variant="outlined" />}
                      {sc.en_proceso > 0 && <Chip label={'En Proceso: ' + sc.en_proceso} size="small" color="info" variant="outlined" />}
                      {sc.canceladas > 0 && <Chip label={'Canceladas: ' + sc.canceladas} size="small" color="error" variant="outlined" />}
                      {totalOrders === 0 && <Typography variant="caption" sx={{ color: '#94A3B8' }}>Sin ordenes</Typography>}
                    </Stack>
                  </CardContent>
                </Card>
              </Stack>
            </Card>
          )}

          {/* KPI Row 2: Balance por moneda */}
          {kpisByCurrency.length > 0 && (
            <Card sx={{ mb: 3, p: 2.5 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#64748B', mb: 2, textTransform: 'uppercase', fontSize: '0.7rem', letterSpacing: 1 }}>
                {'Flujo del Dia por Moneda (' + selectedDay + ')'}
              </Typography>
              <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap', gap: 2 }}>
                {kpisByCurrency.map((bc) => (
                  <Card key={bc.currency} variant="outlined" sx={{
                    flex: '1 1 calc(25% - 16px)', minWidth: 200,
                    borderColor: bc.net > 0 ? '#16A34A40' : bc.net < 0 ? '#DC262640' : '#E2E8F0',
                    backgroundColor: bc.net > 0 ? '#F0FDF4' : bc.net < 0 ? '#FEF2F2' : '#FAFAFA',
                  }}>
                    <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                        <Chip label={getCurrencySymbol(bc.currency) + ' ' + bc.currency} size="small" sx={{ fontWeight: 800, backgroundColor: '#4B2E8315', color: '#4B2E83' }} />
                        <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                          {bc.countries + (bc.countries === 1 ? ' pais' : ' paises')}
                        </Typography>
                      </Stack>
                      <Typography variant="h5" sx={{
                        fontWeight: 800, mb: 0.5,
                        color: bc.net > 0 ? '#16A34A' : bc.net < 0 ? '#DC2626' : '#94A3B8',
                      }}>
                        {getCurrencySymbol(bc.currency) + ' ' + formatMoney(bc.net, bc.currency)}
                      </Typography>
                      <Stack direction="row" spacing={2}>
                        <Typography variant="caption" sx={{ color: '#16A34A' }}>{'Entr: ' + formatMoney(bc.totalIn, bc.currency)}</Typography>
                        <Typography variant="caption" sx={{ color: '#DC2626' }}>{'Sal: ' + formatMoney(bc.totalOut, bc.currency)}</Typography>
                      </Stack>
                    </CardContent>
                  </Card>
                ))}
              </Stack>
            </Card>
          )}

          {/* Warnings */}
          {pendingVerifCount > 0 && (
            <Alert severity="warning" sx={{ mb: 3, fontWeight: 600 }} icon={<WarningIcon />}>
              {'Hay ' + pendingVerifCount + ' ordenes en ORIGEN_VERIFICANDO para este dia. Considera verificarlas antes de cerrar.'}
            </Alert>
          )}

          {/* TABS */}
          <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ mb: 3, '& .MuiTab-root': { fontWeight: 600 } }}>
            <Tab label={'Cierre (' + report.length + ')'} />
            <Tab label={'Depositos (' + movements.length + ')'} />
            <Tab label={'Retiros (' + sweeps.length + ')'} />
          </Tabs>

          {/* TAB 0: Close Report */}
          {activeTab === 0 && (
            <>
              <Card sx={{ mb: 3 }}>
                <CardContent sx={{ p: 0 }}>
                  <Box sx={{ p: 2.5 }}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Box>
                        <Typography variant="h6" sx={{ fontWeight: 700 }}>Detalle por Pais / Moneda</Typography>
                        <Typography variant="body2" sx={{ color: '#64748B', mt: 0.25 }}>
                          {report.length + ' combinaciones | ' + closedCount + ' cerradas | ' + readyToCloseCount + ' listas | ' + notReadyCount + ' pendientes'}
                        </Typography>
                      </Box>
                      <Stack direction="row" spacing={1}>
                        {readyToCloseCount > 0 && (
                          <Button variant="outlined" startIcon={<LockIcon />} size="small"
                            onClick={() => setBatchMode('safe')}
                            disabled={closeLoading}
                            sx={{ color: '#16A34A', borderColor: '#16A34A' }}>
                            {'Cerrar Listas (' + readyToCloseCount + ')'}
                          </Button>
                        )}
                        {notReadyCount > 0 && (
                          <Button variant="outlined" startIcon={<WarningIcon />} size="small"
                            onClick={() => setBatchMode('force')}
                            disabled={closeLoading}
                            sx={{ color: '#DC2626', borderColor: '#DC2626' }}>
                            {'Forzar Todas (' + (report.length - closedCount) + ')'}
                          </Button>
                        )}
                      </Stack>
                    </Stack>
                  </Box>
                  <Divider />
                  <TableContainer sx={{ maxHeight: 500 }}>
                    <Table stickyHeader>
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ fontWeight: 700 }}>Pais</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>Saldo Inicial</TableCell>
                          <TableCell sx={{ fontWeight: 700 }}>Moneda</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700, color: '#16A34A' }}>Entradas</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700, color: '#DC2626' }}>Salidas</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700, color: '#2563EB' }}>Neto</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700, color: '#16A34A' }}>Saldo Final</TableCell>
                          <TableCell align="center" sx={{ fontWeight: 700 }}>Pendientes</TableCell>
                          <TableCell align="center" sx={{ fontWeight: 700 }}>Estado</TableCell>
                          <TableCell align="center" sx={{ fontWeight: 700 }}>Accion</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {report.length === 0 ? (
                          <TableRow>
                            <TableCell colSpan={8} align="center" sx={{ py: 6 }}>
                              <Typography variant="body2" color="text.secondary">No hay datos de billeteras para este dia</Typography>
                            </TableCell>
                          </TableRow>
                        ) : (
                          report.map((item, idx) => (
                            <TableRow key={idx} hover sx={{
                              backgroundColor: item.closed ? '#F0FDF408' : 'inherit',
                              opacity: item.closed ? 0.85 : 1,
                            }}>
                              <TableCell>
                                <Stack direction="row" spacing={1.5} alignItems="center">
                                  <CountryBadge country={item.origin_country} />
                                  <Typography sx={{ fontWeight: 700, fontSize: '0.95rem' }}>{item.origin_country}</Typography>
                                </Stack>
                              </TableCell>
                              <TableCell align="right" sx={{ color: '#64748B', fontWeight: 600 }}>
                                {(() => {
                                  const bal = balances.find(b => b.origin_country === item.origin_country && b.fiat_currency === item.fiat_currency);
                                  return bal ? getCurrencySymbol(item.fiat_currency) + ' ' + formatMoney(bal.opening_balance, item.fiat_currency) : '-';
                                })()}
                              </TableCell>
                              <TableCell>
                                <Chip label={getCurrencySymbol(item.fiat_currency) + ' ' + item.fiat_currency} size="small"
                                  sx={{ fontWeight: 700, backgroundColor: '#4B2E8310', color: '#4B2E83' }} />
                              </TableCell>
                              <TableCell align="right" sx={{ color: '#16A34A', fontWeight: 600 }}>
                                {getCurrencySymbol(item.fiat_currency) + ' ' + formatMoney(item.in_amount, item.fiat_currency)}
                              </TableCell>
                              <TableCell align="right" sx={{ color: '#DC2626', fontWeight: 600 }}>
                                {getCurrencySymbol(item.fiat_currency) + ' ' + formatMoney(item.out_amount, item.fiat_currency)}
                              </TableCell>
                              <TableCell align="right" sx={{
                                fontWeight: 800, fontSize: '1.05rem',
                                color: item.net_amount > 0 ? '#2563EB' : item.net_amount < 0 ? '#DC2626' : '#94A3B8',
                              }}>
                                {getCurrencySymbol(item.fiat_currency) + ' ' + formatMoney(item.net_amount, item.fiat_currency)}
                              </TableCell>
                              <TableCell align="right" sx={{ color: '#16A34A', fontWeight: 700, fontSize: '1rem' }}>
                                {(() => {
                                  const bal = balances.find(b => b.origin_country === item.origin_country && b.fiat_currency === item.fiat_currency);
                                  return bal ? getCurrencySymbol(item.fiat_currency) + ' ' + formatMoney(bal.current_balance, item.fiat_currency) : '-';
                                })()}
                              </TableCell>
                              <TableCell align="center">
                                {item.pending_origin_verificando_count > 0 ? (
                                  <Chip label={item.pending_origin_verificando_count + ' pend.'} size="small" color="warning" sx={{ fontWeight: 700 }} />
                                ) : (
                                  <Chip label="0" size="small" variant="outlined" sx={{ color: '#94A3B8' }} />
                                )}
                              </TableCell>
                              <TableCell align="center">
                                {item.closed ? (
                                  <Tooltip title={'Cerrado: ' + (item.closed_at ? new Date(item.closed_at).toLocaleString('es-VE') : '') + (item.close_note ? ' | ' + item.close_note : '')} arrow>
                                    <Chip icon={<CheckIcon />} label="Cerrado" size="small" color="success" sx={{ fontWeight: 700 }} />
                                  </Tooltip>
                                ) : item.ok_to_close ? (
                                  <Chip label="Listo" size="small" variant="outlined" color="success" sx={{ fontWeight: 600 }} />
                                ) : (
                                  <Tooltip title="Saldo neto != 0 u ordenes pendientes" arrow>
                                    <Chip icon={<WarningIcon />} label="Revisar" size="small" color="warning" sx={{ fontWeight: 600 }} />
                                  </Tooltip>
                                )}
                              </TableCell>
                              <TableCell align="center">
                                {item.closed ? (
                                  <Typography variant="caption" sx={{ color: '#94A3B8' }}>
                                    {'Neto: ' + getCurrencySymbol(item.fiat_currency) + ' ' + formatMoney(item.net_amount_at_close || 0, item.fiat_currency)}
                                  </Typography>
                                ) : (
                                  <Button size="small" variant="outlined" startIcon={<LockIcon />}
                                    onClick={() => handleOpenClose(item)}
                                    sx={{ fontWeight: 700, color: '#4B2E83', borderColor: '#4B2E83', fontSize: '0.75rem' }}>
                                    Cerrar
                                  </Button>
                                )}
                              </TableCell>
                            </TableRow>
                          ))
                        )}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>

              {/* Volume by origin */}
              {dailySummary && dailySummary.volume_by_origin_amount_origin.length > 0 && (
                <Card sx={{ mb: 3 }}>
                  <CardContent sx={{ p: 2.5 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#64748B', mb: 2, textTransform: 'uppercase', fontSize: '0.7rem', letterSpacing: 1 }}>
                      Volumen por Pais de Origen
                    </Typography>
                    <Stack spacing={1}>
                      {dailySummary.volume_by_origin_amount_origin.map((v) => (
                        <Stack key={v.origin_country} direction="row" justifyContent="space-between" alignItems="center"
                          sx={{ p: 1.5, borderRadius: 2, backgroundColor: '#FAFAFA' }}>
                          <Stack direction="row" spacing={1.5} alignItems="center">
                            <CountryBadge country={v.origin_country} />
                            <Typography sx={{ fontWeight: 700 }}>{v.origin_country}</Typography>
                          </Stack>
                          <Typography sx={{ fontWeight: 800, color: '#4B2E83' }}>
                            {v.amount_origin_sum.toLocaleString('es-VE', { minimumFractionDigits: 2 })}
                          </Typography>
                        </Stack>
                      ))}
                    </Stack>
                  </CardContent>
                </Card>
              )}
            </>
          )}

          {/* TAB 1: Depositos del dia */}
          {activeTab === 1 && (
            <Card>
              <CardContent sx={{ p: 0 }}>
                <Box sx={{ p: 2.5 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>Depositos del Dia</Typography>
                      <Typography variant="body2" sx={{ color: '#64748B', mt: 0.25 }}>Fondos fiat recibidos en cuentas de origen</Typography>
                    </Box>
                    <Chip label={movements.length + ' movimientos'} color="success" variant="outlined" sx={{ fontWeight: 700 }} />
                  </Stack>
                </Box>
                <Divider />
                <TableContainer sx={{ maxHeight: 500 }}>
                  <Table stickyHeader size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 700 }}>Hora</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Pais</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>Saldo Inicial</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Moneda</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700 }}>Monto</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Origen</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Estado</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Nota</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {movements.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={7} align="center" sx={{ py: 6 }}>
                            <Typography variant="body2" color="text.secondary">Sin depositos este dia</Typography>
                          </TableCell>
                        </TableRow>
                      ) : (
                        movements.map((m, i) => (
                          <TableRow key={i} hover>
                            <TableCell sx={{ color: '#64748B', fontSize: '0.8rem', fontFamily: 'monospace' }}>
                              {m.created_at ? new Date(m.created_at).toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '-'}
                            </TableCell>
                            <TableCell>
                              <Stack direction="row" spacing={1} alignItems="center">
                                <CountryBadge country={m.origin_country} />
                                <Typography sx={{ fontWeight: 600, fontSize: '0.85rem' }}>{m.origin_country}</Typography>
                              </Stack>
                            </TableCell>
                            <TableCell><Chip label={m.fiat_currency} size="small" variant="outlined" sx={{ fontWeight: 700 }} /></TableCell>
                            <TableCell align="right" sx={{ color: '#16A34A', fontWeight: 700, fontSize: '0.95rem' }}>
                              {'+' + getCurrencySymbol(m.fiat_currency) + ' ' + formatMoney(m.amount_fiat || 0, m.fiat_currency)}
                            </TableCell>
                            <TableCell>
                              {m.ref_order_public_id ? (
                                <Chip label={'Orden #' + m.ref_order_public_id} size="small"
                                  sx={{ fontWeight: 700, color: '#4B2E83', backgroundColor: '#4B2E8312', cursor: 'pointer' }}
                                  onClick={() => window.open('/orders/' + m.ref_order_public_id, '_blank')} />
                              ) : (
                                <Chip label="Manual" size="small" color="warning" variant="outlined" sx={{ fontWeight: 600 }} />
                              )}
                            </TableCell>
                            <TableCell>
                              {m.approved_at ? (
                                <Chip label="Verificado" size="small" color="success" sx={{ fontWeight: 600, fontSize: '0.7rem' }} />
                              ) : (
                                <Chip label="Pendiente" size="small" color="warning" sx={{ fontWeight: 600, fontSize: '0.7rem' }} />
                              )}
                            </TableCell>
                            <TableCell sx={{ color: '#64748B', fontSize: '0.8rem', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {m.note || '-'}
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          )}

          {/* TAB 2: Retiros/Sweeps del dia */}
          {activeTab === 2 && (
            <Card>
              <CardContent sx={{ p: 0 }}>
                <Box sx={{ p: 2.5 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>Retiros / Sweeps del Dia</Typography>
                      <Typography variant="body2" sx={{ color: '#64748B', mt: 0.25 }}>Fondos retirados de cuentas de origen</Typography>
                    </Box>
                    <Chip label={sweeps.length + ' retiros'} color="error" variant="outlined" sx={{ fontWeight: 700 }} />
                  </Stack>
                </Box>
                <Divider />
                <TableContainer sx={{ maxHeight: 500 }}>
                  <Table stickyHeader size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 700 }}>Hora</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Pais</TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700 }}>Saldo Inicial</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Moneda</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700 }}>Monto</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Nota</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Ref. Externa</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>ID</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {sweeps.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={7} align="center" sx={{ py: 6 }}>
                            <Typography variant="body2" color="text.secondary">Sin retiros este dia</Typography>
                          </TableCell>
                        </TableRow>
                      ) : (
                        sweeps.map((s) => (
                          <TableRow key={s.id} hover>
                            <TableCell sx={{ color: '#64748B', fontSize: '0.8rem', fontFamily: 'monospace' }}>
                              {s.created_at ? new Date(s.created_at).toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '-'}
                            </TableCell>
                            <TableCell>
                              <Stack direction="row" spacing={1} alignItems="center">
                                <CountryBadge country={s.origin_country} />
                                <Typography sx={{ fontWeight: 600, fontSize: '0.85rem' }}>{s.origin_country}</Typography>
                              </Stack>
                            </TableCell>
                            <TableCell><Chip label={s.fiat_currency} size="small" variant="outlined" sx={{ fontWeight: 700 }} /></TableCell>
                            <TableCell align="right" sx={{ fontWeight: 700, color: '#DC2626', fontSize: '0.95rem' }}>
                              {'-' + getCurrencySymbol(s.fiat_currency) + ' ' + formatMoney(s.amount_fiat || 0, s.fiat_currency)}
                            </TableCell>
                            <TableCell sx={{ color: '#64748B', fontSize: '0.8rem' }}>{s.note || '-'}</TableCell>
                            <TableCell>
                              {s.external_ref ? (
                                <Chip label={s.external_ref} size="small" variant="outlined" sx={{ fontWeight: 600, fontSize: '0.7rem' }} />
                              ) : (
                                <Typography variant="caption" sx={{ color: '#94A3B8' }}>-</Typography>
                              )}
                            </TableCell>
                            <TableCell>
                              <Typography variant="caption" sx={{ fontFamily: 'monospace', color: '#94A3B8' }}>{'#' + s.id}</Typography>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Close Dialog (per row) */}
      <Dialog open={!!closeTarget} onClose={() => setCloseTarget(null)} fullWidth maxWidth="xs" PaperProps={{ sx: { borderRadius: 3 } }}>
        {closeTarget && (
          <>
            <DialogTitle sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Box sx={{ backgroundColor: '#4B2E8315', borderRadius: '10px', p: 0.75, display: 'flex' }}>
                <LockIcon sx={{ color: '#4B2E83', fontSize: 22 }} />
              </Box>
              Cerrar Billetera
            </DialogTitle>
            <DialogContent>
              <Stack spacing={2.5} sx={{ mt: 1 }}>
                <Alert severity="info" icon={<InfoIcon />}>
                  <Stack spacing={0.5}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <CountryBadge country={closeTarget.origin_country} />
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>{closeTarget.origin_country}</Typography>
                      <Chip label={closeTarget.fiat_currency} size="small" sx={{ fontWeight: 700 }} />
                    </Stack>
                    <Typography variant="caption" sx={{ color: '#64748B' }}>
                      {'Dia: ' + selectedDay + ' | Neto: ' + getCurrencySymbol(closeTarget.fiat_currency) + ' ' + formatMoney(closeTarget.net_amount, closeTarget.fiat_currency)}
                    </Typography>
                  </Stack>
                </Alert>
                {!closeTarget.ok_to_close && (
                  <Alert severity="warning">
                    {'Esta billetera tiene neto != 0 o ' + closeTarget.pending_origin_verificando_count + ' ordenes verificando. Puedes cerrar igualmente (idempotente).'}
                  </Alert>
                )}
                <TextField label="Nota de cierre (opcional)" multiline rows={2} fullWidth
                  value={closeNote} onChange={(e) => setCloseNote(e.target.value)}
                  placeholder="Ej: Cierre normal, conciliado..." />
              </Stack>
            </DialogContent>
            <DialogActions sx={{ p: 2.5, gap: 1 }}>
              <Button onClick={() => setCloseTarget(null)} color="inherit" disabled={closeLoading}>Cancelar</Button>
              <Button variant="contained" onClick={handleConfirmClose} disabled={closeLoading} startIcon={<LockIcon />}
                sx={{ backgroundColor: '#4B2E83', fontWeight: 700, '&:hover': { backgroundColor: '#5A37A0' } }}>
                {closeLoading ? 'Cerrando...' : 'Confirmar Cierre'}
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Batch close dialog */}
      <Dialog open={!!batchMode} onClose={() => setBatchMode(null)} fullWidth maxWidth="xs" PaperProps={{ sx: { borderRadius: 3 } }}>
        <DialogTitle sx={{ fontWeight: 700 }}>
          {batchMode === 'safe' ? 'Cerrar Billeteras Listas' : 'Forzar Cierre Total'}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {batchMode === 'force' && (
              <Alert severity="error">
                {'Vas a cerrar TODAS las billeteras pendientes, incluyendo las que tienen saldo != 0 o pendientes de verificar. Esto es una accion administrativa.'}
              </Alert>
            )}
            {batchMode === 'safe' && (
              <Alert severity="info">
                {'Se cerraran solo las ' + readyToCloseCount + ' billeteras con ok_to_close=true (neto=0 y sin pendientes).'}
              </Alert>
            )}
            <Typography variant="body2" color="text.secondary">
              {'Dia: ' + selectedDay + ' | Billeteras a cerrar: ' + (batchMode === 'safe' ? readyToCloseCount : report.length - closedCount)}
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2.5, gap: 1 }}>
          <Button onClick={() => setBatchMode(null)} color="inherit" disabled={closeLoading}>Cancelar</Button>
          <Button variant="contained" onClick={() => handleBatchClose(batchMode!)} disabled={closeLoading} startIcon={<LockIcon />}
            sx={{
              backgroundColor: batchMode === 'force' ? '#DC2626' : '#4B2E83', fontWeight: 700,
              '&:hover': { backgroundColor: batchMode === 'force' ? '#B91C1C' : '#5A37A0' },
            }}>
            {closeLoading ? 'Cerrando...' : batchMode === 'force' ? 'Forzar Cierre' : 'Cerrar Listas'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar open={snackbar.open} autoHideDuration={5000} onClose={() => setSnackbar((s) => ({ ...s, open: false }))} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert onClose={() => setSnackbar((s) => ({ ...s, open: false }))} severity={snackbar.severity} variant="filled" sx={{ width: '100%', fontWeight: 600 }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}


