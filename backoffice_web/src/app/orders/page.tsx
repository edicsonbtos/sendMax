'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  IconButton,
  Tooltip,
  MenuItem,
  Select,
  FormControl,
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
import api from '@/lib/api';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Table from '@/components/ui/Table';
import Input from '@/components/ui/Input';
import Badge from '@/components/ui/Badge';

interface Order {
  public_id: number | string;
  status: string;
  origin_country: string;
  dest_country: string;
  amount_origin: number;
  origin_currency: string;
  payout_dest: number;
  dest_currency: string;
  profit_usdt: number;
  created_at: string;
  updated_at?: string;
}

interface OrdersResponse {
  count: number;
  orders: Order[];
}

const statusColors: Record<string, 'default' | 'warning' | 'info' | 'success' | 'danger'> = {
  pending_kyc: 'warning',
  pending_origin: 'warning',
  pending_dest: 'info',
  completed: 'success',
  cancelled: 'danger',
  PAGADA: 'success',
  CANCELADA: 'danger',
  PENDIENTE: 'warning',
  EN_PROCESO: 'info',
};

const statusLabels: Record<string, string> = {
  pending_kyc: 'KYC Pendiente',
  pending_origin: 'Pago Origen',
  pending_dest: 'Pago Destino',
  completed: 'Completada',
  cancelled: 'Cancelada',
  PAGADA: 'Pagada',
  CANCELADA: 'Cancelada',
  PENDIENTE: 'Pendiente',
  EN_PROCESO: 'En Proceso',
};

export default function OrdersPage() {
  const router = useRouter();
  const { token, isReady } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [limit, setLimit] = useState(100);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [countryFilter, setCountryFilter] = useState('all');

  const fetchOrders = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const res = await api.get<OrdersResponse>(`/orders?limit=${limit}`);
      const data = res.data;
      const ordersArray = Array.isArray(data?.orders) ? data.orders : [];
      setOrders(ordersArray);
      setFilteredOrders(ordersArray);
    } catch (err: any) {
      const message = err?.response?.data?.detail || err.message || 'Error desconocido';
      setError(message);
      setOrders([]);
      setFilteredOrders([]);
    } finally {
      setLoading(false);
    }
  }, [limit, token]);

  useEffect(() => {
    if (isReady && token) {
      fetchOrders();
    }
  }, [isReady, token, fetchOrders]);

  useEffect(() => {
    let filtered = [...orders];
    if (searchTerm) {
      filtered = filtered.filter((order) => {
        const search = searchTerm.toLowerCase();
        return (
          (order.public_id?.toString() || '').includes(search) ||
          (order.origin_country || '').toLowerCase().includes(search) ||
          (order.dest_country || '').toLowerCase().includes(search) ||
          (order.status || '').toLowerCase().includes(search)
        );
      });
    }
    if (statusFilter !== 'all') {
      filtered = filtered.filter((order) => order.status === statusFilter);
    }
    if (countryFilter !== 'all') {
      filtered = filtered.filter(
        (order) => order.origin_country === countryFilter || order.dest_country === countryFilter
      );
    }
    setFilteredOrders(filtered);
  }, [searchTerm, statusFilter, countryFilter, orders]);

  const handleLimitChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value) || 100;
    setLimit(val);
  };

  const clearFilters = () => {
    setSearchTerm('');
    setStatusFilter('all');
    setCountryFilter('all');
  };

  const exportCSV = () => {
    const headers = ['ID', 'Estado', 'Origen', 'Destino', 'Monto Origen', 'Payout Destino', 'Ganancia', 'Fecha'];
    const rows = filteredOrders.map(o => [
      o.public_id,
      o.status,
      o.origin_country,
      o.dest_country,
      o.amount_origin,
      o.payout_dest,
      o.profit_usdt || 0,
      new Date(o.created_at).toLocaleDateString('es-VE'),
    ]);
    const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `ordenes_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const uniqueStatuses = Array.from(new Set(orders.map(o => o.status).filter(Boolean)));
  const uniqueCountries = Array.from(
    new Set([
      ...orders.map(o => o.origin_country).filter(Boolean),
      ...orders.map(o => o.dest_country).filter(Boolean),
    ])
  ).sort();

  const totalProfit = filteredOrders.reduce((sum, o) => sum + (o.profit_usdt || 0), 0);

  const columns = [
    { 
      key: 'public_id', 
      header: 'ID de Orden',
      render: (o: Order) => (
        <span className="font-bold text-blue-400">#{o.public_id}</span>
      )
    },
    { 
      key: 'status', 
      header: 'Estado',
      render: (o: Order) => (
        <Badge color={statusColors[o.status] || 'default'}>
          {statusLabels[o.status] || o.status}
        </Badge>
      )
    },
    { key: 'origin_country', header: 'Origen' },
    { key: 'dest_country', header: 'Destino' },
    { 
      key: 'amount_origin', 
      header: 'Monto Origen',
      render: (o: Order) => (
        <div className="text-right">
          <div className="font-bold text-white">
            {o.amount_origin?.toLocaleString('es-VE', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[10px] text-gray-500 font-bold uppercase">{o.origin_currency}</div>
        </div>
      )
    },
    { 
      key: 'payout_dest', 
      header: 'Payout Destino',
      render: (o: Order) => (
        <div className="text-right">
          <div className="font-bold text-white">
            {o.payout_dest?.toLocaleString('es-VE', { minimumFractionDigits: 2 })}
          </div>
          <div className="text-[10px] text-gray-500 font-bold uppercase">{o.dest_currency}</div>
        </div>
      )
    },
    { 
      key: 'profit_usdt', 
      header: 'Ganancia',
      render: (o: Order) => (
        <div className="flex items-center justify-end gap-1 font-bold text-emerald-400">
          {(o.profit_usdt || 0) > 0 && <GainIcon sx={{ fontSize: 14 }} />}
          ${(o.profit_usdt || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 })}
        </div>
      )
    },
    { 
      key: 'created_at', 
      header: 'Fecha',
      render: (o: Order) => (
        <div className="text-xs">
          <div className="text-gray-300 font-medium">{new Date(o.created_at).toLocaleDateString('es-VE')}</div>
          <div className="text-gray-500 font-medium">
            {new Date(o.created_at).toLocaleTimeString('es-VE', { hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
      )
    },
    {
      key: 'actions',
      header: 'Acciones',
      render: (o: Order) => (
        <div className="flex justify-center">
          <Tooltip title="Ver detalle">
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                router.push(`/orders/${o.public_id}`);
              }}
              className="text-white/40 hover:text-blue-400 hover:bg-white/5"
            >
              <ViewIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </div>
      )
    }
  ];

  if (!isReady || !token) return null;

  return (
    <div className="space-y-8 pb-10">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-black text-white tracking-tight">
            Órdenes
          </h1>
          <p className="text-gray-500 font-medium mt-1 flex items-center gap-2">
            <span className="text-blue-400 font-bold">{filteredOrders.length}</span> de {orders.length} órdenes detectadas
            {totalProfit > 0 && (
              <>
                <span className="text-gray-700">•</span>
                <span>Ganancia acumulada: <span className="text-emerald-400 font-bold">${totalProfit.toFixed(2)}</span></span>
              </>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3 w-full md:w-auto">
          <Button
            variant="secondary"
            icon={<DownloadIcon sx={{ fontSize: 18 }} />}
            onClick={exportCSV}
            disabled={filteredOrders.length === 0}
            className="flex-1 md:flex-none"
          >
            Exportar CSV
          </Button>
          <Button
            variant="primary"
            icon={<RefreshIcon sx={{ fontSize: 18 }} />}
            onClick={fetchOrders}
            loading={loading}
            className="flex-1 md:flex-none"
          >
            Actualizar
          </Button>
        </div>
      </div>

      {/* Filters Bar */}
      <Card className="p-4 md:p-6 bg-primary-800/20">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-end">
          <div className="md:col-span-5">
            <Input
              label="Búsqueda rápida"
              placeholder="Buscar por ID, país, estado..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              icon={<SearchIcon size={20} />}
            />
          </div>

          <div className="md:col-span-2">
            <FormControl fullWidth size="small" variant="outlined" className="group">
              <label className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 ml-1">Estado</label>
              <Select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-white/5 border-white/10 text-white rounded-xl focus:ring-blue-500/20 group-hover:bg-white/10 transition-all font-medium text-sm"
                MenuProps={{
                  PaperProps: {
                    className: "bg-primary-900 border border-white/10 text-white rounded-xl shadow-2xl"
                  }
                }}
                sx={{
                  color: 'white',
                  '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.1) !important' },
                  '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#3b82f6 !important', borderWidth: '1px !important' },
                  '.MuiSvgIcon-root': { color: 'rgba(255,255,255,0.4)' }
                }}
              >
                <MenuItem value="all">Todos</MenuItem>
                {uniqueStatuses.map(status => (
                  <MenuItem key={status} value={status}>
                    {statusLabels[status] || status}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </div>

          <div className="md:col-span-2">
            <FormControl fullWidth size="small" variant="outlined" className="group">
              <label className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-2 ml-1">País</label>
              <Select
                value={countryFilter}
                onChange={(e) => setCountryFilter(e.target.value)}
                className="bg-white/5 border-white/10 text-white rounded-xl focus:ring-blue-500/20 group-hover:bg-white/10 transition-all font-medium text-sm"
                MenuProps={{
                  PaperProps: {
                    className: "bg-primary-900 border border-white/10 text-white rounded-xl shadow-2xl"
                  }
                }}
                sx={{
                  color: 'white',
                  '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.1) !important' },
                  '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#3b82f6 !important', borderWidth: '1px !important' },
                  '.MuiSvgIcon-root': { color: 'rgba(255,255,255,0.4)' }
                }}
              >
                <MenuItem value="all">Todos</MenuItem>
                {uniqueCountries.map(country => (
                  <MenuItem key={country} value={country}>
                    {country}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </div>

          <div className="md:col-span-1">
            <Input
              label="Límite"
              type="number"
              value={limit}
              onChange={handleLimitChange}
              className="min-w-[80px]"
            />
          </div>

          {(searchTerm || statusFilter !== 'all' || countryFilter !== 'all') && (
            <div className="md:col-span-2 pb-1">
              <Button
                variant="ghost"
                size="sm"
                icon={<ClearIcon size={16} />}
                onClick={clearFilters}
                className="w-full"
              >
                Limpiar
              </Button>
            </div>
          )}
        </div>
      </Card>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-500 font-semibold flex items-center gap-3 animate-shake">
          <ClearIcon />
          {error}
        </div>
      )}

      <Table
        columns={columns}
        data={filteredOrders}
        loading={loading}
        emptyMessage={orders.length === 0 ? 'No hay órdenes registradas' : 'No hay coincidencias para los filtros'}
        className="animate-slide-up"
      />
    </div>
  );
}
