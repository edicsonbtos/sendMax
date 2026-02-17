'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Box,
  Typography,
  Card,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  TextField,
  Stack,
  Button,
  IconButton,
  Tooltip,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  InputAdornment,
} from '@mui/material';
import {
  Visibility as ViewIcon,
  Refresh as RefreshIcon,
  Search as SearchIcon,
  Download as DownloadIcon,
  TrendingUp as GainIcon,
  Close as ClearIcon,
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import { apiRequest } from '@/lib/api';

interface Order {
  public_id: number;
  status: string;
  origin_country: string;
  dest_country: string;
  amount_origin: number;
  payout_dest: number;
  profit_usdt: number;
  awaiting_paid_proof: boolean;
  created_at: string;
  updated_at?: string;
  paid_at?: string;
}

interface OrdersResponse {
  count: number;
  orders: Order[];
}

const statusColors: Record<string, 'default' | 'warning' | 'info' | 'success' | 'error'> = {
  CREADA: 'warning',
  EN_PROCESO: 'info',
  ORIGEN_VERIFICANDO: 'info',
  PAGADA: 'success',
  CANCELADA: 'error',
  COMPLETADA: 'success',
};

const statusLabels: Record<string, string> = {
  CREADA: 'Creada',
  EN_PROCESO: 'En Proceso',
  ORIGEN_VERIFICANDO: 'Verificando Origen',
  PAGADA: 'Pagada',
  CANCELADA: 'Cancelada',
  COMPLETADA: 'Completada',
};

export default function OrdersPage() {
  const router = useRouter();
  const { token } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [limit, setLimit] = useState(100);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [countryFilter, setCountryFilter] = useState('all');

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await apiRequest<OrdersResponse>(`/orders?limit=${limit}`);
      const ordersArray = Array.isArray(data?.orders) ? data.orders : [];
      setOrders(ordersArray);
      setFilteredOrders(ordersArray);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Error desconocido';
      setError(message);
      setOrders([]);
      setFilteredOrders([]);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    if (token) fetchOrders();
  }, [token, fetchOrders]);

  useEffect(() => {
    let filtered = [...orders];
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter((o) =>
        o.public_id.toString().includes(search) ||
        o.origin_country?.toLowerCase().includes(search) ||
        o.dest_country?.toLowerCase().includes(search) ||
        o.status?.toLowerCase().includes(search)
      );
    }
    if (statusFilter !== 'all') filtered = filtered.filter((o) => o.status === statusFilter);
    if (countryFilter !== 'all') filtered = filtered.filter((o) => o.origin_country === countryFilter || o.dest_country === countryFilter);
    setFilteredOrders(filtered);
  }, [searchTerm, statusFilter, countryFilter, orders]);

  const clearFilters = () => { setSearchTerm(''); setStatusFilter('all'); setCountryFilter('all'); };

  const exportCSV = () => {
    const headers = ['ID', 'Estado', 'Origen', 'Destino', 'Monto Origen', 'Payout Destino', 'Ganancia', 'Fecha', 'Pagada'];
    const rows = filteredOrders.map((o) => [
      o.public_id, o.status, o.origin_country, o.dest_country,
      o.amount_origin, o.payout_dest, o.profit_usdt || 0,
      new Date(o.created_at).toLocaleDateString('es-VE'),
      o.paid_at ? new Date(o.paid_at).toLocaleDateString('es-VE') : 'N/A',
    ]);
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `ordenes_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const uniqueStatuses = Array.from(new Set(orders.map((o) => o.status).filter(Boolean)));
  const uniqueCountries = Array.from(new Set([...orders.map((o) => o.origin_country), ...orders.map((o) => o.dest_country)].filter(Boolean))).sort();
  const totalProfit = filteredOrders.reduce((sum, o) => sum + (o.profit_usdt || 0), 0);

  return (
    <Box className="fade-in">
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>Ordenes</Typography>
          <Typography variant="body2" sx={{ color: '#64748B', mt: 0.5 }}>
            {`${filteredOrders.length} de ${orders.length} ordenes`}
            {totalProfit > 0 && ` | Ganancia filtrada: $${totalProfit.toFixed(2)}`}
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button variant="outlined" startIcon={<DownloadIcon />} onClick={exportCSV} disabled={filteredOrders.length === 0} size="small">CSV</Button>
          <Button variant="contained" startIcon={<RefreshIcon />} onClick={fetchOrders} disabled={loading}>Actualizar</Button>
        </Stack>
      </Stack>

      <Card sx={{ mb: 3, p: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="flex-end">
          <TextField
            size="small"
            placeholder="Buscar por ID, pais, status..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            sx={{ flex: 1, minWidth: 200 }}
            slotProps={{ input: { startAdornment: <InputAdornment position="start"><SearchIcon sx={{ color: '#64748B', fontSize: 20 }} /></InputAdornment> } }}
          />
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Status</InputLabel>
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} label="Status">
              <MenuItem value="all">Todos</MenuItem>
              {uniqueStatuses.map((s) => <MenuItem key={s} value={s}>{statusLabels[s] || s}</MenuItem>)}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Pais</InputLabel>
            <Select value={countryFilter} onChange={(e) => setCountryFilter(e.target.value)} label="Pais">
              <MenuItem value="all">Todos</MenuItem>
              {uniqueCountries.map((c) => <MenuItem key={c} value={c}>{c}</MenuItem>)}
            </Select>
          </FormControl>
          <TextField size="small" type="number" label="Limite" value={limit} onChange={(e) => setLimit(parseInt(e.target.value) || 100)} sx={{ width: 100 }} />
          {(searchTerm || statusFilter !== 'all' || countryFilter !== 'all') && (
            <Button size="small" startIcon={<ClearIcon />} onClick={clearFilters} sx={{ color: '#64748B' }}>Limpiar</Button>
          )}
        </Stack>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress sx={{ color: '#4B2E83' }} />
        </Box>
      ) : (
        <Card>
          <TableContainer sx={{ maxHeight: 600 }}>
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>ID</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell>Ruta</TableCell>
                  <TableCell align="right">Monto Origen</TableCell>
                  <TableCell align="right">Payout Destino</TableCell>
                  <TableCell align="right">Ganancia</TableCell>
                  <TableCell>Fecha</TableCell>
                  <TableCell align="center">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredOrders.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} align="center" sx={{ py: 6 }}>
                      <Typography variant="body2" color="text.secondary">
                        {orders.length === 0 ? 'No hay ordenes' : 'Sin resultados con los filtros actuales'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredOrders.map((order) => (
                    <TableRow
                      key={order.public_id}
                      hover
                      sx={{ cursor: 'pointer', '&:hover': { backgroundColor: '#FAF8FF' } }}
                      onClick={() => router.push(`/orders/${order.public_id}`)}
                    >
                      <TableCell>
                        <Typography sx={{ fontFamily: 'monospace', fontSize: '0.875rem', fontWeight: 600, color: '#4B2E83' }}>
                          {`#${order.public_id}`}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={statusLabels[order.status] || order.status}
                          color={statusColors[order.status] || 'default'}
                          size="small"
                          sx={{ fontWeight: 600 }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {`${order.origin_country} → ${order.dest_country}`}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {order.amount_origin?.toLocaleString('es-VE', { minimumFractionDigits: 2 })}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {order.payout_dest?.toLocaleString('es-VE', { minimumFractionDigits: 2 })}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Stack direction="row" spacing={0.5} alignItems="center" justifyContent="flex-end">
                          {order.profit_usdt > 0 && <GainIcon sx={{ fontSize: 14, color: '#16A34A' }} />}
                          <Typography variant="body2" sx={{ color: order.profit_usdt > 0 ? '#16A34A' : '#64748B', fontWeight: 600 }}>
                            {`$${(order.profit_usdt || 0).toFixed(2)}`}
                          </Typography>
                        </Stack>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{new Date(order.created_at).toLocaleDateString('es-VE')}</Typography>
                        <Typography variant="caption" sx={{ color: '#64748B' }}>
                          {new Date(order.created_at).toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' })}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Tooltip title="Ver detalle">
                          <IconButton size="small" onClick={(e) => { e.stopPropagation(); router.push(`/orders/${order.public_id}`); }}>
                            <ViewIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Card>
      )}
    </Box>
  );
}

