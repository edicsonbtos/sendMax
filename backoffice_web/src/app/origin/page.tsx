'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box, Typography, Card, CardContent, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Button, Chip, CircularProgress,
  Alert, Dialog, DialogTitle, DialogContent, DialogActions, TextField,
  Stack, Divider, Tabs, Tab, IconButton, Tooltip, Snackbar,
  Switch, FormControlLabel, Avatar,
} from '@mui/material';
import {
  Refresh as RefreshIcon, AccountBalanceWallet as WalletIcon,
  TrendingUp as InIcon, TrendingDown as OutIcon,
  AccountBalance as BankIcon, Download as DownloadIcon,
  Add as AddIcon, Remove as RemoveIcon,
  DeleteSweep as EmptyIcon, Info as InfoIcon,
  Public as GlobeIcon,
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

/* -- Interfaces ------------------------------------------- */
interface WalletBalance {
  origin_country: string;
  fiat_currency: string;
  total_in: number;
  total_out: number;
  current_balance: number;
}

interface BalancesResponse {
  ok: boolean;
  items: WalletBalance[];
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

type ModalAction = 'deposit' | 'withdraw' | 'empty' | null;

/* -- Helpers ---------------------------------------------- */
const formatMoney = (amount: number, currency: string) => {
  const decimals = ['COP', 'VES', 'CLP'].includes(currency) ? 0 : 2;
  return amount.toLocaleString('es-VE', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
};

const getCurrencySymbol = (currency: string) => {
  const symbols: Record<string, string> = {
    USD: '$', USDT: '$', COP: 'COL$', PEN: 'S/', VES: 'Bs.',
    CLP: 'CLP$', ARS: 'AR$', BRL: 'R$', MXN: 'MX$', BOB: 'Bs',
    EUR: 'EUR', GBP: 'GBP',
  };
  return symbols[currency] || currency;
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
    ESPANA: { code: 'ES', color: '#AA151B' },
  };
  return info[country.toUpperCase()] || { code: country.substring(0, 2), color: '#64748B' };
};

/* -- Componente ------------------------------------------- */
export default function OriginWalletsPage() {
  const { apiKey } = useAuth();

  const [wallets, setWallets] = useState<WalletBalance[]>([]);
  const [sweeps, setSweeps] = useState<SweepItem[]>([]);
  const [dailyMovements, setDailyMovements] = useState<DailyMovement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showZeroBalance, setShowZeroBalance] = useState(false);

  const [activeTab, setActiveTab] = useState(0);

  const [modalOpen, setModalOpen] = useState(false);
  const [modalAction, setModalAction] = useState<ModalAction>(null);
  const [selectedWallet, setSelectedWallet] = useState<WalletBalance | null>(null);
  const [actionAmount, setActionAmount] = useState('');
  const [actionNote, setActionNote] = useState('');
  const [actionRef, setActionRef] = useState('');
  const [processing, setProcessing] = useState(false);

  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'success' as 'success' | 'error' });

  const today = useMemo(() => new Date().toISOString().split('T')[0], []);

  /* -- Fetch ---------------------------------------------- */
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [balancesData, sweepsData, dailyData] = await Promise.all([
        apiRequest<BalancesResponse>('/origin-wallets/current-balances'),
        apiRequest<SweepsResponse>('/origin-wallets/sweeps?day=' + today).catch(() => ({ ok: true, day: today, count: 0, sweeps: [] as SweepItem[] })),
        apiRequest<DailyResponse>('/origin-wallets/daily?day=' + today).catch(() => ({ ok: true, day: today, totals: [], movements: [] as DailyMovement[] })),
      ]);
      setWallets(balancesData?.items || []);
      setSweeps(sweepsData?.sweeps || []);
      setDailyMovements(dailyData?.movements || []);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error de conexion';
      setError(message);
      setWallets([]);
    } finally {
      setLoading(false);
    }
  }, [today]);

  useEffect(() => {
    if (apiKey) fetchData();
  }, [apiKey, fetchData]);

  /* -- Wallets filtradas ---------------------------------- */
  const displayWallets = useMemo(() => {
    if (showZeroBalance) return wallets;
    return wallets.filter((w) => w.current_balance !== 0);
  }, [wallets, showZeroBalance]);

  const walletsWithZero = useMemo(() => wallets.filter((w) => w.current_balance === 0).length, [wallets]);

  /* -- Totales por moneda --------------------------------- */
  const balancesByCurrency = useMemo(() => {
    const map: Record<string, { currency: string; totalIn: number; totalOut: number; balance: number; countries: number }> = {};
    wallets.forEach((w) => {
      if (!map[w.fiat_currency]) {
        map[w.fiat_currency] = { currency: w.fiat_currency, totalIn: 0, totalOut: 0, balance: 0, countries: 0 };
      }
      map[w.fiat_currency].totalIn += w.total_in || 0;
      map[w.fiat_currency].totalOut += w.total_out || 0;
      map[w.fiat_currency].balance += w.current_balance || 0;
      map[w.fiat_currency].countries += 1;
    });
    return Object.values(map).sort((a, b) => b.balance - a.balance);
  }, [wallets]);

  const todayDepositsByCurrency = useMemo(() => {
    const map: Record<string, number> = {};
    dailyMovements.forEach((m) => {
      map[m.fiat_currency] = (map[m.fiat_currency] || 0) + (m.amount_fiat || 0);
    });
    return map;
  }, [dailyMovements]);

  const todaySweepsByCurrency = useMemo(() => {
    const map: Record<string, number> = {};
    sweeps.forEach((s) => {
      map[s.fiat_currency] = (map[s.fiat_currency] || 0) + (s.amount_fiat || 0);
    });
    return map;
  }, [sweeps]);

  /* -- Modal ---------------------------------------------- */
  const handleOpenModal = (wallet: WalletBalance, action: ModalAction) => {
    setSelectedWallet(wallet);
    setModalAction(action);
    setActionAmount(action === 'empty' ? wallet.current_balance.toFixed(2) : '');
    setActionNote('');
    setActionRef('');
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setModalAction(null);
    setSelectedWallet(null);
  };

  const handleConfirmAction = async () => {
    if (!selectedWallet || !modalAction) return;
    setProcessing(true);

    try {
      const base = {
        day: today,
        origin_country: selectedWallet.origin_country,
        fiat_currency: selectedWallet.fiat_currency,
        note: actionNote || undefined,
        external_ref: actionRef || undefined,
      };

      let endpoint = '';
      let payload: Record<string, unknown> = {};
      let successMsg = '';

      switch (modalAction) {
        case 'deposit':
          endpoint = '/origin-wallets/deposit';
          payload = { ...base, amount_fiat: parseFloat(actionAmount) };
          successMsg = 'Deposito de ' + getCurrencySymbol(selectedWallet.fiat_currency) + ' ' + formatMoney(parseFloat(actionAmount), selectedWallet.fiat_currency) + ' registrado en ' + selectedWallet.origin_country;
          break;
        case 'withdraw':
          endpoint = '/origin-wallets/withdraw';
          payload = { ...base, amount_fiat: parseFloat(actionAmount) };
          successMsg = 'Retiro de ' + getCurrencySymbol(selectedWallet.fiat_currency) + ' ' + formatMoney(parseFloat(actionAmount), selectedWallet.fiat_currency) + ' desde ' + selectedWallet.origin_country;
          break;
        case 'empty':
          if (selectedWallet.current_balance <= 0) {
            setSnackbar({ open: true, message: 'La billetera ya esta vacia', severity: 'error' });
            setProcessing(false);
            return;
          }
          endpoint = '/origin-wallets/sweeps';
          payload = { ...base, amount_fiat: selectedWallet.current_balance, note: actionNote || 'Vaciado completo desde backoffice' };
          successMsg = 'Billetera ' + selectedWallet.origin_country + ' vaciada: ' + getCurrencySymbol(selectedWallet.fiat_currency) + ' ' + formatMoney(selectedWallet.current_balance, selectedWallet.fiat_currency);
          break;
      }

      await apiRequest(endpoint, { method: 'POST', body: JSON.stringify(payload) });
      setSnackbar({ open: true, message: successMsg, severity: 'success' });
      handleCloseModal();
      fetchData();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error en la operacion';
      setSnackbar({ open: true, message, severity: 'error' });
    } finally {
      setProcessing(false);
    }
  };

  /* -- CSV ------------------------------------------------ */
  const exportCSV = () => {
    if (wallets.length === 0) return;
    const headers = ['Pais', 'Moneda', 'Simbolo', 'Total_Entradas', 'Total_Salidas', 'Balance'];
    const rows = wallets.map((w) => [
      w.origin_country, w.fiat_currency, getCurrencySymbol(w.fiat_currency),
      w.total_in.toFixed(2), w.total_out.toFixed(2), w.current_balance.toFixed(2),
    ]);
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'billeteras_origen_' + today + '.csv';
    link.click();
  };

  /* -- Modal Config --------------------------------------- */
  const modalConfig = {
    deposit: { title: 'Depositar Fondos', color: '#16A34A', icon: <AddIcon />, desc: 'Registrar entrada manual de fondos fiat. Esto SUMA al balance.', confirm: 'Confirmar Deposito', showAmount: true },
    withdraw: { title: 'Retirar Fondos', color: '#DC2626', icon: <RemoveIcon />, desc: 'Registrar retiro. El sistema valida saldo suficiente. Esto RESTA del balance.', confirm: 'Confirmar Retiro', showAmount: true },
    empty: { title: 'Vaciar Billetera', color: '#F59E0B', icon: <EmptyIcon />, desc: 'Retirar TODO el saldo disponible. Se registra como sweep.', confirm: 'Vaciar Todo', showAmount: false },
  };
  const cfg = modalAction ? modalConfig[modalAction] : null;
  const isAmountInvalid = modalAction === 'withdraw' && actionAmount !== '' && parseFloat(actionAmount) > (selectedWallet?.current_balance || 0);
  const isConfirmDisabled = processing
    || (cfg?.showAmount && (!actionAmount || parseFloat(actionAmount) <= 0))
    || isAmountInvalid
    || (modalAction === 'empty' && (selectedWallet?.current_balance || 0) <= 0);

  /* -- Country Avatar ------------------------------------- */
  const CountryBadge = ({ country }: { country: string }) => {
    const info = getCountryInfo(country);
    return (
      <Avatar sx={{ width: 28, height: 28, fontSize: '0.7rem', fontWeight: 800, bgcolor: info.color, color: '#fff' }}>
        {info.code}
      </Avatar>
    );
  };

  /* -- RENDER --------------------------------------------- */
  return (
    <Box className="fade-in">
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>Billeteras de Origen</Typography>
          <Typography variant="body2" sx={{ color: '#64748B', mt: 0.5 }}>
            {'Cuentas fiat donde los clientes depositan | ' + today}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" startIcon={<DownloadIcon />} onClick={exportCSV} disabled={wallets.length === 0} size="small">CSV</Button>
          <Button variant="contained" startIcon={<RefreshIcon />} onClick={fetchData} disabled={loading}>Actualizar</Button>
        </Stack>
      </Stack>

      {/* KPI: Balance por moneda */}
      <Card sx={{ mb: 3, p: 2.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#64748B', mb: 2, textTransform: 'uppercase', fontSize: '0.7rem', letterSpacing: 1 }}>
          Balance Consolidado por Moneda
        </Typography>
        <Stack direction="row" spacing={2} sx={{ flexWrap: 'wrap', gap: 2 }}>
          {balancesByCurrency.length === 0 ? (
            <Typography variant="body2" sx={{ color: '#94A3B8' }}>Sin datos</Typography>
          ) : (
            balancesByCurrency.map((bc) => (
              <Card key={bc.currency} variant="outlined" sx={{
                flex: '1 1 calc(25% - 16px)', minWidth: 200,
                borderColor: bc.balance > 0 ? '#16A34A40' : bc.balance < 0 ? '#DC262640' : '#E2E8F0',
                backgroundColor: bc.balance > 0 ? '#F0FDF4' : bc.balance < 0 ? '#FEF2F2' : '#FAFAFA',
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
                    color: bc.balance > 0 ? '#16A34A' : bc.balance < 0 ? '#DC2626' : '#94A3B8',
                  }}>
                    {getCurrencySymbol(bc.currency) + ' ' + formatMoney(bc.balance, bc.currency)}
                  </Typography>
                  <Stack direction="row" spacing={2}>
                    <Typography variant="caption" sx={{ color: '#16A34A' }}>{'Entr: ' + formatMoney(bc.totalIn, bc.currency)}</Typography>
                    <Typography variant="caption" sx={{ color: '#DC2626' }}>{'Sal: ' + formatMoney(bc.totalOut, bc.currency)}</Typography>
                  </Stack>
                </CardContent>
              </Card>
            ))
          )}
        </Stack>
      </Card>

      {/* KPI: Movimientos de hoy */}
      <Card sx={{ mb: 3, p: 2.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#64748B', mb: 2, textTransform: 'uppercase', fontSize: '0.7rem', letterSpacing: 1 }}>
          {'Movimientos de Hoy (' + today + ')'}
        </Typography>
        <Stack direction="row" spacing={3} sx={{ flexWrap: 'wrap', gap: 2 }}>
          <Box>
            <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.5 }}>
              <InIcon sx={{ fontSize: 16, color: '#16A34A' }} />
              <Typography variant="caption" sx={{ fontWeight: 700, color: '#16A34A' }}>{dailyMovements.length + ' depositos'}</Typography>
            </Stack>
            {Object.entries(todayDepositsByCurrency).length === 0 ? (
              <Typography variant="caption" sx={{ color: '#94A3B8' }}>Sin depositos hoy</Typography>
            ) : (
              Object.entries(todayDepositsByCurrency).map(([cur, amt]) => (
                <Typography key={cur} variant="body2" sx={{ fontWeight: 600, color: '#16A34A' }}>
                  {'+' + getCurrencySymbol(cur) + ' ' + formatMoney(amt, cur)}
                </Typography>
              ))
            )}
          </Box>
          <Divider orientation="vertical" flexItem />
          <Box>
            <Stack direction="row" spacing={0.5} alignItems="center" sx={{ mb: 0.5 }}>
              <OutIcon sx={{ fontSize: 16, color: '#DC2626' }} />
              <Typography variant="caption" sx={{ fontWeight: 700, color: '#DC2626' }}>{sweeps.length + ' retiros'}</Typography>
            </Stack>
            {Object.entries(todaySweepsByCurrency).length === 0 ? (
              <Typography variant="caption" sx={{ color: '#94A3B8' }}>Sin retiros hoy</Typography>
            ) : (
              Object.entries(todaySweepsByCurrency).map(([cur, amt]) => (
                <Typography key={cur} variant="body2" sx={{ fontWeight: 600, color: '#DC2626' }}>
                  {'-' + getCurrencySymbol(cur) + ' ' + formatMoney(amt, cur)}
                </Typography>
              ))
            )}
          </Box>
        </Stack>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {/* Tabs */}
      <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ mb: 3, '& .MuiTab-root': { fontWeight: 600 } }}>
        <Tab label={'Balances (' + displayWallets.length + ')'} />
        <Tab label={'Entradas Hoy (' + dailyMovements.length + ')'} />
        <Tab label={'Salidas Hoy (' + sweeps.length + ')'} />
      </Tabs>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress sx={{ color: '#4B2E83' }} />
        </Box>
      ) : (
        <>
          {/* TAB 0: Balances */}
          {activeTab === 0 && (
            <Card>
              <CardContent sx={{ p: 0 }}>
                <Box sx={{ p: 2.5 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>Balance por Pais</Typography>
                      <Typography variant="body2" sx={{ color: '#64748B', mt: 0.25 }}>
                        Balance = Total Entradas - Total Salidas (historico). Las billeteras nuevas aparecen cuando reciben su primer deposito.
                      </Typography>
                    </Box>
                    {walletsWithZero > 0 && (
                      <FormControlLabel
                        control={<Switch size="small" checked={showZeroBalance} onChange={(e) => setShowZeroBalance(e.target.checked)} />}
                        label={<Typography variant="caption" sx={{ color: '#64748B' }}>{'Mostrar vacias (' + walletsWithZero + ')'}</Typography>}
                      />
                    )}
                  </Stack>
                </Box>
                <Divider />
                <TableContainer sx={{ maxHeight: 500 }}>
                  <Table stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 700 }}>Pais</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Moneda</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700, color: '#16A34A' }}>Total Entradas</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700, color: '#DC2626' }}>Total Salidas</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700, color: '#2563EB' }}>Balance</TableCell>
                        <TableCell align="center" sx={{ fontWeight: 700 }}>Acciones</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {displayWallets.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={6} align="center" sx={{ py: 6 }}>
                            <Typography variant="body2" color="text.secondary">
                              {wallets.length === 0 ? 'No hay billeteras con movimientos' : 'Todas las billeteras estan en 0'}
                            </Typography>
                            {walletsWithZero > 0 && !showZeroBalance && (
                              <Button size="small" sx={{ mt: 1 }} onClick={() => setShowZeroBalance(true)}>
                                {'Mostrar ' + walletsWithZero + ' vacias'}
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      ) : (
                        displayWallets.map((w, i) => (
                          <TableRow key={i} hover sx={{
                            '&:hover': { backgroundColor: '#FAFAFE' },
                            opacity: w.current_balance === 0 ? 0.5 : 1,
                          }}>
                            <TableCell>
                              <Stack direction="row" spacing={1.5} alignItems="center">
                                <CountryBadge country={w.origin_country} />
                                <Typography sx={{ fontWeight: 700, fontSize: '0.95rem' }}>{w.origin_country}</Typography>
                              </Stack>
                            </TableCell>
                            <TableCell>
                              <Chip label={getCurrencySymbol(w.fiat_currency) + ' ' + w.fiat_currency} size="small"
                                sx={{ fontWeight: 700, backgroundColor: '#4B2E8310', color: '#4B2E83' }} />
                            </TableCell>
                            <TableCell align="right" sx={{ color: '#16A34A', fontWeight: 600 }}>
                              {getCurrencySymbol(w.fiat_currency) + ' ' + formatMoney(w.total_in, w.fiat_currency)}
                            </TableCell>
                            <TableCell align="right" sx={{ color: '#DC2626', fontWeight: 600 }}>
                              {getCurrencySymbol(w.fiat_currency) + ' ' + formatMoney(w.total_out, w.fiat_currency)}
                            </TableCell>
                            <TableCell align="right" sx={{
                              fontWeight: 800, fontSize: '1.05rem',
                              color: w.current_balance > 0 ? '#2563EB' : w.current_balance < 0 ? '#DC2626' : '#94A3B8',
                            }}>
                              {getCurrencySymbol(w.fiat_currency) + ' ' + formatMoney(w.current_balance, w.fiat_currency)}
                            </TableCell>
                            <TableCell align="center">
                              <Stack direction="row" spacing={0.5} justifyContent="center">
                                <Tooltip title="Depositar" arrow>
                                  <IconButton size="small" onClick={() => handleOpenModal(w, 'deposit')}
                                    sx={{ color: '#16A34A', border: '1px solid #16A34A30', '&:hover': { backgroundColor: '#16A34A12' } }}>
                                    <AddIcon fontSize="small" />
                                  </IconButton>
                                </Tooltip>
                                <Tooltip title="Retirar" arrow>
                                  <span>
                                    <IconButton size="small" onClick={() => handleOpenModal(w, 'withdraw')}
                                      disabled={w.current_balance <= 0}
                                      sx={{ color: '#DC2626', border: '1px solid #DC262630', '&:hover': { backgroundColor: '#DC262612' } }}>
                                      <RemoveIcon fontSize="small" />
                                    </IconButton>
                                  </span>
                                </Tooltip>
                                <Tooltip title="Vaciar todo" arrow>
                                  <span>
                                    <IconButton size="small" onClick={() => handleOpenModal(w, 'empty')}
                                      disabled={w.current_balance <= 0}
                                      sx={{ color: '#F59E0B', border: '1px solid #F59E0B30', '&:hover': { backgroundColor: '#F59E0B12' } }}>
                                      <EmptyIcon fontSize="small" />
                                    </IconButton>
                                  </span>
                                </Tooltip>
                              </Stack>
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

          {/* TAB 1: Entradas hoy */}
          {activeTab === 1 && (
            <Card>
              <CardContent sx={{ p: 0 }}>
                <Box sx={{ p: 2.5 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>Depositos Recibidos Hoy</Typography>
                      <Typography variant="body2" sx={{ color: '#64748B', mt: 0.25 }}>Fondos fiat que entraron a cuentas de origen</Typography>
                    </Box>
                    <Chip label={dailyMovements.length + ' movimientos'} color="success" variant="outlined" sx={{ fontWeight: 700 }} />
                  </Stack>
                </Box>
                <Divider />
                <TableContainer sx={{ maxHeight: 500 }}>
                  <Table stickyHeader size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 700 }}>Hora</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Pais</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Moneda</TableCell>
                        <TableCell align="right" sx={{ fontWeight: 700 }}>Monto</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Origen</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Estado</TableCell>
                        <TableCell sx={{ fontWeight: 700 }}>Nota</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {dailyMovements.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={7} align="center" sx={{ py: 6 }}>
                            <Typography variant="body2" color="text.secondary">Sin depositos hoy</Typography>
                          </TableCell>
                        </TableRow>
                      ) : (
                        dailyMovements.map((m, i) => (
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
                            <TableCell>
                              <Chip label={m.fiat_currency} size="small" variant="outlined" sx={{ fontWeight: 700 }} />
                            </TableCell>
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

          {/* TAB 2: Salidas hoy */}
          {activeTab === 2 && (
            <Card>
              <CardContent sx={{ p: 0 }}>
                <Box sx={{ p: 2.5 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Box>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>Retiros / Sweeps de Hoy</Typography>
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
                            <Typography variant="body2" color="text.secondary">Sin retiros hoy</Typography>
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
                            <TableCell>
                              <Chip label={s.fiat_currency} size="small" variant="outlined" sx={{ fontWeight: 700 }} />
                            </TableCell>
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

      {/* -- Modal -- */}
      <Dialog open={modalOpen} onClose={handleCloseModal} fullWidth maxWidth="xs" PaperProps={{ sx: { borderRadius: 3 } }}>
        {cfg && selectedWallet && (
          <>
            <DialogTitle sx={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 1.5, pb: 1 }}>
              <Box sx={{ backgroundColor: cfg.color + '15', borderRadius: '10px', p: 0.75, display: 'flex' }}>
                {React.cloneElement(cfg.icon, { sx: { color: cfg.color, fontSize: 22 } })}
              </Box>
              {cfg.title}
            </DialogTitle>
            <DialogContent>
              <Stack spacing={2.5} sx={{ mt: 1 }}>
                <Alert severity="info" icon={<WalletIcon />} sx={{ '& .MuiAlert-message': { width: '100%' } }}>
                  <Stack direction="row" justifyContent="space-between" sx={{ width: '100%' }}>
                    <Box>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <CountryBadge country={selectedWallet.origin_country} />
                        <Typography variant="body2" sx={{ fontWeight: 700 }}>{selectedWallet.origin_country}</Typography>
                      </Stack>
                      <Typography variant="caption" sx={{ color: '#64748B' }}>{getCurrencySymbol(selectedWallet.fiat_currency) + ' ' + selectedWallet.fiat_currency}</Typography>
                    </Box>
                    <Box sx={{ textAlign: 'right' }}>
                      <Typography variant="body2" sx={{ fontWeight: 700, color: selectedWallet.current_balance > 0 ? '#2563EB' : '#DC2626' }}>
                        {getCurrencySymbol(selectedWallet.fiat_currency) + ' ' + formatMoney(selectedWallet.current_balance, selectedWallet.fiat_currency)}
                      </Typography>
                      <Typography variant="caption" sx={{ color: '#64748B' }}>Balance actual</Typography>
                    </Box>
                  </Stack>
                </Alert>
                <Typography variant="body2" sx={{ color: '#475569', lineHeight: 1.5 }}>{cfg.desc}</Typography>
                {cfg.showAmount && (
                  <TextField
                    label={'Monto (' + getCurrencySymbol(selectedWallet.fiat_currency) + ' ' + selectedWallet.fiat_currency + ')'}
                    type="number" fullWidth value={actionAmount}
                    onChange={(e) => setActionAmount(e.target.value)}
                    placeholder="0.00" error={isAmountInvalid}
                    helperText={isAmountInvalid ? 'Excede el balance disponible' : modalAction === 'deposit' ? 'Se SUMARA al balance' : 'Max: ' + formatMoney(selectedWallet.current_balance, selectedWallet.fiat_currency)}
                    slotProps={{ input: { sx: { fontSize: '1.3rem', fontWeight: 700 } } }}
                    autoFocus
                  />
                )}
                {modalAction === 'empty' && (
                  <Alert severity="warning">
                    {'Se retiraran '}<strong>{getCurrencySymbol(selectedWallet.fiat_currency) + ' ' + formatMoney(selectedWallet.current_balance, selectedWallet.fiat_currency)}</strong>{' (todo el saldo)'}
                  </Alert>
                )}
                <TextField label="Nota / Descripcion" multiline rows={2} fullWidth value={actionNote}
                  onChange={(e) => setActionNote(e.target.value)}
                  placeholder={modalAction === 'deposit' ? 'Ej: Recarga banco nacional...' : 'Ej: Transferencia a Binance...'} />
                <TextField label="Referencia Externa (opcional)" fullWidth size="small" value={actionRef}
                  onChange={(e) => setActionRef(e.target.value)} placeholder="Ej: TXN-12345, ref bancaria..."
                  helperText="Para conciliar con extracto bancario" />
              </Stack>
            </DialogContent>
            <DialogActions sx={{ p: 2.5, gap: 1 }}>
              <Button onClick={handleCloseModal} color="inherit" disabled={processing}>Cancelar</Button>
              <Button onClick={handleConfirmAction} variant="contained" disabled={isConfirmDisabled}
                sx={{ backgroundColor: cfg.color, fontWeight: 700, '&:hover': { backgroundColor: cfg.color + 'CC' } }}>
                {processing ? 'Procesando...' : cfg.confirm}
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Snackbar */}
      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar((s) => ({ ...s, open: false }))} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
        <Alert onClose={() => setSnackbar((s) => ({ ...s, open: false }))} severity={snackbar.severity} variant="filled" sx={{ width: '100%', fontWeight: 600 }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
