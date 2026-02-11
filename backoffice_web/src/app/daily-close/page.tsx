'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Stack,
  Button,
  TextField,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Divider,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Download as DownloadIcon,
  Lock as LockIcon,
  CheckCircle as CheckIcon,
  Refresh as RefreshIcon,
  TrendingUp as InIcon,
  TrendingDown as OutIcon,
  AccountBalance as BalanceIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

interface CloseReportItem {
  country: string;
  currency: string;
  total_in: number;
  total_out: number;
  net_balance: number;
}

interface CloseReportResponse {
  report?: CloseReportItem[];
  items?: CloseReportItem[];
  data?: CloseReportItem[];
}

interface CloseResponse {
  status: string;
  day: string;
  message: string;
  closed_at?: string;
}

export default function DailyClosePage() {
  const { apiKey } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedDay, setSelectedDay] = useState('');
  const [report, setReport] = useState<CloseReportItem[]>([]);
  const [closeDialogOpen, setCloseDialogOpen] = useState(false);
  const [closeLoading, setCloseLoading] = useState(false);
  const [closeResult, setCloseResult] = useState<CloseResponse | null>(null);

  useEffect(() => {
    const today = new Date();
    today.setDate(today.getDate() - 1);
    const formatted = today.toISOString().split('T')[0];
    setSelectedDay(formatted);
  }, []);

  const fetchReport = useCallback(async () => {
    if (!selectedDay) return;
    setLoading(true);
    setError('');
    setCloseResult(null);
    try {
      const data = await apiRequest<CloseReportResponse | CloseReportItem[]>(`/origin-wallets/close-report?day=${selectedDay}`);
      const reportArray = Array.isArray(data) ? data : (data.report || data.items || data.data || []);
      setReport(reportArray);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error desconocido';
      setError(message);
      setReport([]);
    } finally {
      setLoading(false);
    }
  }, [selectedDay]);

  useEffect(() => {
    if (selectedDay && apiKey) {
      fetchReport();
    }
  }, [selectedDay, apiKey, fetchReport]);

  const handleCloseDay = async () => {
    setCloseLoading(true);
    setError('');
    try {
      const result = await apiRequest<CloseResponse>('/origin-wallets/close', {
        method: 'POST',
        body: JSON.stringify({ day: selectedDay }),
      });
      setCloseResult(result);
      setCloseDialogOpen(false);
      fetchReport();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error desconocido';
      setError(message);
    } finally {
      setCloseLoading(false);
    }
  };

  const exportCSV = () => {
    if (!Array.isArray(report) || report.length === 0) return;
    const headers = ['Pais', 'Moneda', 'Entradas', 'Salidas', 'Balance Neto'];
    const rows = report.map(r => [
      r.country,
      r.currency,
      (r.total_in || 0).toFixed(2),
      (r.total_out || 0).toFixed(2),
      (r.net_balance || 0).toFixed(2),
    ]);
    const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `cierre_${selectedDay}.csv`;
    link.click();
  };

  const safeReport = Array.isArray(report) ? report : [];
  const totalIn = safeReport.reduce((sum, r) => sum + (r.total_in || 0), 0);
  const totalOut = safeReport.reduce((sum, r) => sum + (r.total_out || 0), 0);
  const totalNet = safeReport.reduce((sum, r) => sum + (r.net_balance || 0), 0);

  return (
    <Box className="fade-in">
      {/* Header */}
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800 }}>
            Cierre Diario
          </Typography>
          <Typography variant="body2" sx={{ color: '#64748B', mt: 0.5 }}>
            Reporte de cierre y consolidacion por dia
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<RefreshIcon />}
          onClick={fetchReport}
          disabled={loading}
        >
          Actualizar
        </Button>
      </Stack>

      {/* Filtros */}
      <Card sx={{ mb: 3 }}>
        <CardContent sx={{ p: 2.5 }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="flex-end">
            <TextField
              type="date"
              label="Dia a cerrar"
              value={selectedDay}
              onChange={(e) => setSelectedDay(e.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              sx={{ width: 220 }}
              size="small"
            />
            <Button variant="outlined" onClick={fetchReport} disabled={loading}>
              Consultar Reporte
            </Button>
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={exportCSV}
              disabled={safeReport.length === 0}
            >
              Exportar CSV
            </Button>
            <Box sx={{ flex: 1 }} />
            <Chip
              label={selectedDay}
              size="small"
              sx={{ backgroundColor: '#EFEAFF', color: '#4B2E83', fontWeight: 700 }}
            />
          </Stack>
        </CardContent>
      </Card>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {closeResult && (
        <Alert
          severity={closeResult.status === 'already_closed' ? 'info' : 'success'}
          sx={{ mb: 3 }}
          icon={<CheckIcon />}
        >
          <strong>{closeResult.message}</strong>
          {closeResult.closed_at && (
            <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
              Cerrado el: {new Date(closeResult.closed_at).toLocaleString('es-VE')}
            </Typography>
          )}
        </Alert>
      )}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress sx={{ color: '#4B2E83' }} />
        </Box>
      ) : (
        <>
          {/* Resumen KPIs */}
          <Stack direction="row" spacing={2.5} sx={{ mb: 3, flexWrap: 'wrap', gap: 2 }}>
            <Card sx={{ flex: '1 1 calc(33.33% - 16px)', minWidth: 220 }}>
              <CardContent sx={{ p: 2.5 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                  <Box>
                    <Typography variant="body2" sx={{ color: '#64748B', fontSize: '0.8rem' }}>
                      Total Entradas
                    </Typography>
                    <Typography variant="h5" sx={{ fontWeight: 800, color: '#16A34A', mt: 0.75 }}>
                      {`$${totalIn.toLocaleString('es-VE', { minimumFractionDigits: 2 })}`}
                    </Typography>
                  </Box>
                  <Box sx={{ backgroundColor: '#16A34A12', borderRadius: '14px', p: 1.25, display: 'flex' }}>
                    <InIcon sx={{ color: '#16A34A', fontSize: 24 }} />
                  </Box>
                </Stack>
              </CardContent>
            </Card>

            <Card sx={{ flex: '1 1 calc(33.33% - 16px)', minWidth: 220 }}>
              <CardContent sx={{ p: 2.5 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                  <Box>
                    <Typography variant="body2" sx={{ color: '#64748B', fontSize: '0.8rem' }}>
                      Total Salidas
                    </Typography>
                    <Typography variant="h5" sx={{ fontWeight: 800, color: '#DC2626', mt: 0.75 }}>
                      {`$${totalOut.toLocaleString('es-VE', { minimumFractionDigits: 2 })}`}
                    </Typography>
                  </Box>
                  <Box sx={{ backgroundColor: '#DC262612', borderRadius: '14px', p: 1.25, display: 'flex' }}>
                    <OutIcon sx={{ color: '#DC2626', fontSize: 24 }} />
                  </Box>
                </Stack>
              </CardContent>
            </Card>

            <Card sx={{ flex: '1 1 calc(33.33% - 16px)', minWidth: 220 }}>
              <CardContent sx={{ p: 2.5 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                  <Box>
                    <Typography variant="body2" sx={{ color: '#64748B', fontSize: '0.8rem' }}>
                      Balance Neto
                    </Typography>
                    <Typography variant="h5" sx={{ fontWeight: 800, color: totalNet >= 0 ? '#2563EB' : '#DC2626', mt: 0.75 }}>
                      {`$${totalNet.toLocaleString('es-VE', { minimumFractionDigits: 2 })}`}
                    </Typography>
                  </Box>
                  <Box sx={{ backgroundColor: '#2563EB12', borderRadius: '14px', p: 1.25, display: 'flex' }}>
                    <BalanceIcon sx={{ color: '#2563EB', fontSize: 24 }} />
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          </Stack>

          {/* Tabla detalle */}
          <Card sx={{ mb: 3 }}>
            <CardContent sx={{ p: 0 }}>
              <Box sx={{ p: 2.5 }}>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  Detalle por Pais / Moneda
                </Typography>
                <Typography variant="body2" sx={{ color: '#64748B', mt: 0.25 }}>
                  {`Resumen del dia ${selectedDay}`}
                </Typography>
              </Box>

              <Divider />

              <TableContainer sx={{ maxHeight: 480 }}>
                <Table stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>Pais</TableCell>
                      <TableCell>Moneda</TableCell>
                      <TableCell align="right">Entradas</TableCell>
                      <TableCell align="right">Salidas</TableCell>
                      <TableCell align="right">Balance Neto</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {safeReport.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={5} align="center" sx={{ py: 6 }}>
                          <Typography variant="body2" color="text.secondary">
                            No hay datos para este dia
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      safeReport.map((item, idx) => (
                        <TableRow key={idx} hover>
                          <TableCell sx={{ fontWeight: 600 }}>{item.country}</TableCell>
                          <TableCell>
                            <Chip label={item.currency} size="small" sx={{ fontWeight: 700 }} />
                          </TableCell>
                          <TableCell align="right" sx={{ color: '#16A34A', fontWeight: 600 }}>
                            {`$${(item.total_in || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 })}`}
                          </TableCell>
                          <TableCell align="right" sx={{ color: '#DC2626', fontWeight: 600 }}>
                            {`$${(item.total_out || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 })}`}
                          </TableCell>
                          <TableCell align="right" sx={{ fontWeight: 800, color: item.net_balance >= 0 ? '#2563EB' : '#DC2626' }}>
                            {`$${(item.net_balance || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 })}`}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>

          {/* Boton de cierre */}
          <Card sx={{ backgroundColor: '#FFF5E6', border: '1px solid #F59E0B' }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems="center" spacing={2}>
                <Stack direction="row" spacing={2} alignItems="center">
                  <Box sx={{ backgroundColor: '#F59E0B15', borderRadius: '14px', p: 1.25, display: 'flex' }}>
                    <WarningIcon sx={{ color: '#F59E0B', fontSize: 28 }} />
                  </Box>
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 700, color: '#92400E' }}>
                      Accion de Cierre
                    </Typography>
                    <Typography variant="body2" sx={{ color: '#92400E', opacity: 0.8 }}>
                      El cierre es <strong>idempotente</strong>. Si ya fue cerrado, no se duplicara.
                    </Typography>
                  </Box>
                </Stack>
                <Button
                  variant="contained"
                  size="large"
                  startIcon={<LockIcon />}
                  onClick={() => setCloseDialogOpen(true)}
                  disabled={safeReport.length === 0}
                  sx={{
                    backgroundColor: '#4B2E83',
                    px: 4,
                    py: 1.5,
                    '&:hover': { backgroundColor: '#5A37A0' },
                  }}
                >
                  {`Cerrar Dia ${selectedDay}`}
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </>
      )}

      {/* Dialog confirmacion */}
      <Dialog open={closeDialogOpen} onClose={() => setCloseDialogOpen(false)}>
        <DialogTitle sx={{ fontWeight: 700 }}>Confirmar Cierre Diario</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            <Alert severity="warning">
              Estas a punto de cerrar el dia <strong>{selectedDay}</strong>.
            </Alert>
            <Typography variant="body2" color="text.secondary">
              El cierre registrara los balances finales de cada pais y moneda para este dia.
              Si ya fue cerrado anteriormente, se devolvera el resultado existente sin duplicar.
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={() => setCloseDialogOpen(false)}>Cancelar</Button>
          <Button
            variant="contained"
            onClick={handleCloseDay}
            disabled={closeLoading}
            startIcon={<LockIcon />}
            sx={{ backgroundColor: '#4B2E83', '&:hover': { backgroundColor: '#5A37A0' } }}
          >
            {closeLoading ? 'Cerrando...' : 'Confirmar Cierre'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}