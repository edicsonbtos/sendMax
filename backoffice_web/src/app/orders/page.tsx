'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';
import api from '@/lib/api';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import DataTable from '@/components/ui/DataTable';
import Input from '@/components/ui/Input';
import Badge from '@/components/ui/Badge';
import SectionHeader from '@/components/ui/SectionHeader';
import MetricCard from '@/components/ui/MetricCard';
import FilterBar from '@/components/ui/FilterBar';
import EmptyState from '@/components/ui/EmptyState';
import LoadingState from '@/components/ui/LoadingState';
import MoneyCell from '@/components/ui/MoneyCell';
import { DollarSign, RefreshCcw, Download, Search, FilterX, TrendingUp, Filter, Eye, AlertCircle } from 'lucide-react';

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
    { key: 'origin_country', header: 'Origen', render: (o: Order) => o.origin_country },
    { key: 'dest_country', header: 'Destino', render: (o: Order) => o.dest_country },
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
          {(o.profit_usdt || 0) > 0 && <TrendingUp size={14} />}
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
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              router.push(`/orders/${o.public_id}`);
            }}
            className="text-white/40 hover:text-blue-400 hover:bg-white/5 p-1"
            title="Ver detalle"
          >
            <Eye size={16} />
          </Button>
        </div>
      )
    }
  ];

  if (!isReady || !token) return null;

  return (
    <div className="space-y-8 pb-10">
      {/* Header */}
      <SectionHeader
        title="Órdenes"
        subtitle={`${filteredOrders.length} de ${orders.length} órdenes detectadas`}
        rightSlot={
          <>
            <Button
              variant="secondary"
              icon={<Download size={18} />}
              onClick={exportCSV}
              disabled={filteredOrders.length === 0}
            >
              Exportar
            </Button>
            <Button
              variant="primary"
              icon={<RefreshCcw size={18} className={loading ? "animate-spin" : ""} />}
              onClick={fetchOrders}
              loading={loading}
            >
              Actualizar
            </Button>
          </>
        }
      />

      {/* Stats Summary */}
      {totalProfit > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <MetricCard
            label="Ganancia Comercial"
            value={<MoneyCell value={totalProfit} emphasize />}
            icon={<DollarSign size={24} />}
            hint="Suma acumulada de órdenes filtradas"
          />
        </div>
      )}

      {/* Filters Bar */}
      <FilterBar>
        <div className="flex-1 min-w-[300px]">
          <Input
            label="Búsqueda rápida"
            placeholder="Buscar por ID, país, estado..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            icon={<Search size={18} />}
          />
        </div>

        <div className="w-full lg:w-48">
          <div className="flex flex-col gap-2">
            <label className="block text-[10px] font-bold text-white/40 uppercase tracking-[0.2em] ml-1">Estado</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-white/5 border border-white/10 text-white rounded-xl h-10 px-3 text-sm focus:ring-blue-500/20 outline-none w-full"
            >
              <option value="all" className="bg-primary-900 font-bold">Todos los Estados</option>
              {uniqueStatuses.map(status => (
                <option key={status} value={status} className="bg-primary-900 font-bold">
                  {statusLabels[status] || status}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="w-full lg:w-48">
          <div className="flex flex-col gap-2">
            <label className="block text-[10px] font-bold text-white/40 uppercase tracking-[0.2em] ml-1">País</label>
            <select
              value={countryFilter}
              onChange={(e) => setCountryFilter(e.target.value)}
              className="bg-white/5 border border-white/10 text-white rounded-xl h-10 px-3 text-sm focus:ring-blue-500/20 outline-none w-full"
            >
              <option value="all" className="bg-primary-900 font-bold">Todos los Países</option>
              {uniqueCountries.map(country => (
                <option key={country} value={country} className="bg-primary-900 font-bold">
                  {country}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="w-full lg:w-24">
          <Input
            label="Límite"
            type="number"
            value={limit}
            onChange={handleLimitChange}
            className="h-10"
          />
        </div>

        {(searchTerm || statusFilter !== 'all' || countryFilter !== 'all') && (
          <div className="pb-1">
            <Button
              variant="ghost"
              size="sm"
              icon={<FilterX size={16} />}
              onClick={clearFilters}
              className="lg:mt-6"
            >
              Limpiar
            </Button>
          </div>
        )}
      </FilterBar>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-500 font-semibold flex items-center gap-3 animate-shake">
          <AlertCircle />
          {error}
        </div>
      )}

      {loading ? (
        <LoadingState title="Consultando historial de órdenes..." />
      ) : filteredOrders.length === 0 ? (
        <EmptyState
          title="Sin órdenes encontradas"
          description={orders.length === 0 ? 'No hay órdenes registradas en el sistema todavía.' : 'No hay coincidencias para los filtros aplicados.'}
          action={
            <Button variant="secondary" onClick={clearFilters} icon={<FilterX size={16} />}>
              Limpiar filtros
            </Button>
          }
        />
      ) : (
        <DataTable<Order>
          columns={columns}
          data={filteredOrders}
          loading={loading}
          rowKey={(o) => o.public_id}
          className="animate-slide-up"
        />
      )}
    </div>
  );
}
