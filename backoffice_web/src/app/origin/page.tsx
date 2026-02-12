'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Stack,
  Divider,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  AccountBalanceWallet as WalletIcon,
  TrendingUp as InIcon,
  TrendingDown as OutIcon,
  AccountBalance as BankIcon,
  Download as DownloadIcon,
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

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
  origin_country: string;
  fiat_currency: string;
  amount: number;
  note: string;
  created_at: string;
}

interface SweepsResponse {
  items?: SweepItem[];
}

export default function OriginWalletsPage() {
  const { apiKey } = useAuth();
  const [wallets, setWallets] = useState<WalletBalance[]>([]);
  const [sweeps, setSweeps] = useState<SweepItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [withdrawOpen, setWithdrawOpen] = useState(false);
  const [selectedWallet, setSelectedWallet] = useState<WalletBalance | null>(null);
  const [withdrawAmount, setWithdrawAmount] = useState('');
  const [withdrawNote, setWithdrawNote] = useState('');
  const [withdrawing, setWithdrawing] = useState(false);
  const [withdrawSuccess, setWithdrawSuccess] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const today = new Date().toISOString().split('T')[0];
      const [balancesData, sweepsData] = await Promise.all([
        apiRequest<BalancesResponse>('/origin-wallets/current-balances'),
        apiRequest<SweepsResponse>('/origin-wallets/sweeps?day=' + today).catch(() => ({ items: [] })),
      ]);
      const items = balancesData?.items || [];
      setWallets(items);
      const sweepsArray = Array.isArray(sweepsData) ? sweepsData : (sweepsData?.items || []);
      setSweeps(sweepsArray);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error desconocido';
      setError(message);
      setWallets([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (apiKey) fetchData();
  }, [apiKey, fetchData]);

  const totalIn = useMemo(() => wallets.reduce((s, w) => s + (w.total_in || 0), 0), [wallets]);
  const totalOut = useMemo(() => wallets.reduce((s, w) => s + (w.total_out || 0), 0), [wallets]);
  const totalBalance = useMemo(() => wallets.reduce((s, w) => s + (w.current_balance || 0), 0), [wallets]);

  const handleOpenWithdraw = (wallet: WalletBalance) => {
    setSelectedWallet(wallet);
    setWithdrawAmount(wallet.current_balance > 0 ? wallet.current_balance.toString() : '');
    setWithdrawNote('');
    setWithdrawSuccess('');
    setWithdrawOpen(true);
  };

  const handleCloseWithdraw = () => {
    setWithdrawOpen(false);
    setSelectedWallet(null);
    setWithdrawSuccess('');
  };

  const handleConfirmWithdraw = async () => {
    if (!selectedWallet) return;
    setWithdrawing(true);
    setError('');
    try {
      await apiRequest('/origin-wallets/sweeps', {
        method: 'POST',
        body: JSON.stringify({
          origin_country: selectedWallet.origin_country,
          fiat_currency: selectedWallet.fiat_currency,
          amount_fiat: parseFloat(withdrawAmount),
          day: new Date().toISOString().split('T')[0],
          note: withdrawNote || 'Retiro desde backoffice',
        }),
      });
      setWithdrawSuccess('Retiro de ' + withdrawAmount + ' ' + selectedWallet.fiat_currency + ' registrado');
      fetchData();
      setTimeout(() => handleCloseWithdraw(), 2000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error en el retiro';
      setError(message);
    } finally {
      setWithdrawing(false);
    }
  };

  const exportCSV = () => {
    if (wallets.length === 0) return;
    const headers = ['Pais', 'Moneda', 'Entradas', 'Salidas', 'Balance'];
    const rows = wallets.map((w) => [
      w.origin_country, w.fiat_currency,
      w.total_in.toFixed(2), w.total_out.toFixed(2), w.current_balance.toFixed(2),
    ]);
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'wallets_origen_' + new Date().toISOString().split('T')[0] + '.csv';
    link.click();
  };

  return (
    <Box className="fade-in">
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>Billeteras de Origen</Typography>
          <Typography variant="body2" sx={{ color: '#64748B', mt: 0.5 }}>
            {wallets.length + ' paises con saldo | Balance consolidado por moneda'}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" startIcon={<DownloadIcon />} onClick={exportCSV} disabled={wallets.length === 0} size="small">CSV</Button>
          <Button variant="contained" startIcon={<RefreshIcon />} onClick={fetchData} disabled={loading}>Actualizar</Button>
        </Stack>
      </Stack>

      <Stack direction="row" spacing={2.5} sx={{ mb: 4, flexWrap: 'wrap', gap: 2 }}>
        <Card sx={{ flex: '1 1 calc(25% - 16px)', minWidth: 200 }}>
          <CardContent sx={{ p: 2.5 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
              <Box>
                <Typography variant="body2" sx={{ color: '#64748B', fontSize: '0.8rem', mb: 0.5 }}>Total Paises</Typography>
                <Typography variant="h4" sx={{ fontWeight: 700, color: '#111827' }}>{wallets.length}</Typography>
                <Typography variant="caption" sx={{ color: '#64748B' }}>Cuentas con movimiento</Typography>
              </Box>
              <Box sx={{ backgroundColor: '#4B2E8312', borderRadius: '14px', p: 1.25 }}>
                <BankIcon sx={{ color: '#4B2E83', fontSize: 26 }} />
              </Box>
            </Stack>
          </CardContent>
        </Card>

        <Card sx={{ flex: '1 1 calc(25% - 16px)', minWidth: 200 }}>
          <CardContent sx={{ p: 2.5 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
              <Box>
                <Typography variant="body2" sx={{ color: '#64748B', fontSize: '0.8rem', mb: 0.5 }}>Total Entradas</Typography>
                <Typography variant="h4" sx={{ fontWeight: 700, color: '#16A34A' }}>{totalIn.toLocaleString('es-VE', { minimumFractionDigits: 0 })}</Typography>
                <Typography variant="caption" sx={{ color: '#64748B' }}>Suma todas las monedas</Typography>
              </Box>
              <Box sx={{ backgroundColor: '#16A34A12', borderRadius: '14px', p: 1.25 }}>
                <InIcon sx={{ color: '#16A34A', fontSize: 26 }} />
              </Box>
            </Stack>
          </CardContent>
        </Card>

        <Card sx={{ flex: '1 1 calc(25% - 16px)', minWidth: 200 }}>
          <CardContent sx={{ p: 2.5 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
              <Box>
                <Typography variant="body2" sx={{ color: '#64748B', fontSize: '0.8rem', mb: 0.5 }}>Total Salidas</Typography>
                <Typography variant="h4" sx={{ fontWeight: 700, color: '#DC2626' }}>{totalOut.toLocaleString('es-VE', { minimumFractionDigits: 0 })}</Typography>
                <Typography variant="caption" sx={{ color: '#64748B' }}>Retiros y sweeps</Typography>
              </Box>
              <Box sx={{ backgroundColor: '#DC262612', borderRadius: '14px', p: 1.25 }}>
                <OutIcon sx={{ color: '#DC2626', fontSize: 26 }} />
              </Box>
            </Stack>
          </CardContent>
        </Card>

        <Card sx={{ flex: '1 1 calc(25% - 16px)', minWidth: 200 }}>
          <CardContent sx={{ p: 2.5 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
              <Box>
                <Typography variant="body2" sx={{ color: '#64748B', fontSize: '0.8rem', mb: 0.5 }}>Balance Neto</Typography>
                <Typography variant="h4" sx={{ fontWeight: 700, color: totalBalance >= 0 ? '#2563EB' : '#DC2626' }}>{totalBalance.toLocaleString('es-VE', { minimumFractionDigits: 0 })}</Typography>
                <Typography variant="caption" sx={{ color: '#64748B' }}>Fondos disponibles</Typography>
              </Box>
              <Box sx={{ backgroundColor: '#2563EB12', borderRadius: '14px', p: 1.25 }}>
                <WalletIcon sx={{ color: '#2563EB', fontSize: 26 }} />
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </Stack>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress sx={{ color: '#4B2E83' }} />
        </Box>
      ) : (
        <>
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 0 }}>
              <Box sx={{ p: 2.5 }}>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>Balance por Pais y Moneda</Typography>
                <Typography variant="body2" sx={{ color: '#64748B', mt: 0.25 }}>Saldos actuales en cuentas de origen</Typography>
              </Box>
              <Divider />
              <TableContainer sx={{ maxHeight: 500 }}>
                <Table stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>Pais</TableCell>
                      <TableCell>Moneda</TableCell>
                      <TableCell align="right">Entradas</TableCell>
                      <TableCell align="right">Salidas</TableCell>
                      <TableCell align="right">Balance Actual</TableCell>
                      <TableCell align="center">Acciones</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {wallets.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} align="center" sx={{ py: 6 }}>
                          <Typography variant="body2" color="text.secondary">No hay billeteras con movimientos</Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      wallets.map((w, i) => (
                        <TableRow key={i} hover>
                          <TableCell sx={{ fontWeight: 600 }}>{w.origin_country}</TableCell>
                          <TableCell>
                            <Chip label={w.fiat_currency} size="small" variant="outlined" sx={{ fontWeight: 700 }} />
                          </TableCell>
                          <TableCell align="right" sx={{ color: '#16A34A', fontWeight: 600 }}>
                            {w.total_in.toLocaleString('es-VE', { minimumFractionDigits: 2 })}
                          </TableCell>
                          <TableCell align="right" sx={{ color: '#DC2626', fontWeight: 600 }}>
                            {w.total_out.toLocaleString('es-VE', { minimumFractionDigits: 2 })}
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 800, color: w.current_balance >= 0 ? '#2563EB' : '#DC2626' }}>
                            {w.current_balance.toLocaleString('es-VE', { minimumFractionDigits: 2 })}
                          </TableCell>
                          <TableCell align="center">
                            <Button size="small" variant="outlined" onClick={() => handleOpenWithdraw(w)} disabled={w.current_balance <= 0} sx={{ fontSize: '0.75rem' }}>
                              Retirar
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>

          {sweeps.length > 0 && (
            <Card>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Retiros de Hoy</Typography>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Fecha</TableCell>
                        <TableCell>Pais</TableCell>
                        <TableCell>Moneda</TableCell>
                        <TableCell align="right">Monto</TableCell>
                        <TableCell>Nota</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {sweeps.slice(0, 10).map((s) => (
                        <TableRow key={s.id} hover>
                          <TableCell sx={{ color: '#64748B' }}>{new Date(s.created_at).toLocaleString('es-VE')}</TableCell>
                          <TableCell sx={{ fontWeight: 600 }}>{s.origin_country}</TableCell>
                          <TableCell><Chip label={s.fiat_currency} size="small" sx={{ fontWeight: 700 }} /></TableCell>
                          <TableCell align="right" sx={{ fontWeight: 700, color: '#DC2626' }}>{s.amount.toLocaleString('es-VE', { minimumFractionDigits: 2 })}</TableCell>
                          <TableCell sx={{ color: '#64748B', fontSize: '0.8rem' }}>{s.note || '-'}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          )}
        </>
      )}

      <Dialog open={withdrawOpen} onClose={handleCloseWithdraw} fullWidth maxWidth="xs">
        <DialogTitle sx={{ fontWeight: 700 }}>Registrar Retiro</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {withdrawSuccess ? (
              <Alert severity="success">{withdrawSuccess}</Alert>
            ) : (
              <>
                <Alert severity="info" sx={{ fontSize: '0.85rem' }}>
                  {'Retiro de fondos de '}<strong>{selectedWallet?.origin_country}</strong>{' ('}{selectedWallet?.fiat_currency}{').'}
                  {' Balance actual: '}<strong>{selectedWallet?.current_balance.toLocaleString('es-VE', { minimumFractionDigits: 2 })}</strong>
                </Alert>
                <TextField label="Monto a Retirar" type="number" fullWidth value={withdrawAmount} onChange={(e) => setWithdrawAmount(e.target.value)} />
                <TextField label="Nota / Referencia" multiline rows={2} fullWidth value={withdrawNote} onChange={(e) => setWithdrawNote(e.target.value)} placeholder="Ej: Retiro a Binance..." />
              </>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={handleCloseWithdraw} color="inherit">{withdrawSuccess ? 'Cerrar' : 'Cancelar'}</Button>
          {!withdrawSuccess && (
            <Button onClick={handleConfirmWithdraw} variant="contained" disabled={withdrawing || !withdrawAmount}>
              {withdrawing ? 'Procesando...' : 'Confirmar Retiro'}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
}
