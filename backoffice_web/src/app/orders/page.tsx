'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { useAuth } from '@/components/AuthProvider';
import {
  Search,
  Download,
  RefreshCcw,
  Eye,
  X,
  TrendingUp,
  AlertCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency, formatDateTime } from '@/lib/formatters';
import type { Order } from '@/types';

interface OrdersResponse {
  count: number;
  orders: Order[];
}

const statusStyles: Record<string, string> = {
  CREADA: 'bg-[#f59e0b1a] text-[#f59e0b] border-[#f59e0b4d]',
  EN_PROCESO: 'bg-[#06b6d41a] text-[#06b6d4] border-[#06b6d44d]',
  ORIGEN_VERIFICANDO: 'bg-[#8b5cf61a] text-[#8b5cf6] border-[#8b5cf64d]',
  PAGADA: 'bg-[#10b9811a] text-[#10b981] border-[#10b9814d]',
  CANCELADA: 'bg-[#ef44441a] text-[#ef4444] border-[#ef44444d]',
  COMPLETADA: 'bg-[#10b9811a] text-[#10b981] border-[#10b9814d]',
};

const statusLabels: Record<string, string> = {
  CREADA: 'Creada',
  EN_PROCESO: 'En Proceso',
  ORIGEN_VERIFICANDO: 'Verificando',
  PAGADA: 'Pagada',
  CANCELADA: 'Cancelada',
  COMPLETADA: 'Completada',
};

export default function OrdersPage() {
  const router = useRouter();
  const { token } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);

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
      const res = await api.get<OrdersResponse>(`/orders?limit=${limit}`);
      const data = res.data;
      const ordersArray = Array.isArray(data?.orders) ? data.orders : [];
      setOrders(ordersArray);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Error cargando órdenes');
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    if (token) fetchOrders();
  }, [token, fetchOrders]);

  const filteredOrders = useMemo(() => {
    let filtered = [...orders];
    if (searchTerm) {
      const search = searchTerm.toLowerCase();
      filtered = filtered.filter((o: any) =>
        o.public_id?.toString().includes(search) ||
        o.origin_country?.toLowerCase().includes(search) ||
        o.dest_country?.toLowerCase().includes(search) ||
        o.status?.toLowerCase().includes(search) ||
        o.client_name?.toLowerCase().includes(search)
      );
    }
    if (statusFilter !== 'all') filtered = filtered.filter((o) => o.status === statusFilter);
    if (countryFilter !== 'all') filtered = filtered.filter((o: any) => o.origin_country === countryFilter || o.dest_country === countryFilter);
    return filtered;
  }, [searchTerm, statusFilter, countryFilter, orders]);

  const exportCSV = () => {
    const headers = ['ID', 'Estado', 'Origen', 'Destino', 'Monto Origen', 'Payout Destino', 'Ganancia', 'Fecha'];
    const rows = filteredOrders.map((o: any) => [
      o.public_id, o.status, o.origin_country || 'N/A', o.dest_country || 'N/A',
      o.amount_origin || 0, o.payout_dest || 0, o.profit_usdt || 0,
      formatDateTime(o.created_at)
    ]);
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `ordenes_admin_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const uniqueStatuses = Array.from(new Set(orders.map((o) => o.status).filter(Boolean)));
  const uniqueCountries = Array.from(new Set([...orders.map((o: any) => o.origin_country), ...orders.map((o: any) => o.dest_country)].filter(Boolean))).sort();
  const totalProfit = filteredOrders.reduce((sum, o: any) => sum + (o.profit_real_usdt || o.profit_usdt || 0), 0);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-black bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent tracking-tight">
            Órdenes
          </h1>
          <p className="text-sm font-medium text-gray-400 mt-1">
            {`${filteredOrders.length} de ${orders.length} órdenes recuperadas`}
            {totalProfit > 0 && <span className="ml-2 text-emerald-400 font-bold">| Ganancia mostrada: ${totalProfit.toFixed(2)}</span>}
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={exportCSV}
            disabled={filteredOrders.length === 0}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-gray-500/30 text-gray-300 hover:bg-gray-500/10 transition-all text-sm font-bold disabled:opacity-50"
          >
            <Download size={16} /> CSV
          </button>
          <button
            onClick={fetchOrders}
            disabled={loading}
            className="flex items-center gap-2 px-5 py-2 rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 transition-all text-sm font-bold disabled:opacity-50"
          >
            <RefreshCcw size={16} className={cn(loading && "animate-spin")} />
            Actualizar
          </button>
        </div>
      </div>

      {/* Filters Card */}
      <div className="card-glass p-4 md:p-5">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex-1 min-w-[200px] relative text-gray-400 focus-within:text-cyan-400">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Buscar por ID, nombre..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="input-glass pl-10 text-sm py-2.5 bg-[#ffffff05]"
            />
          </div>

          <div className="w-[160px] flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-widest font-bold text-gray-500 ml-1">Estado</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="input-glass text-sm py-2.5 bg-[#0a0f1e] text-gray-200"
            >
              <option value="all">Todos</option>
              {uniqueStatuses.map((s) => (
                <option key={s} value={s}>{statusLabels[s] || s}</option>
              ))}
            </select>
          </div>

          <div className="w-[160px] flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-widest font-bold text-gray-500 ml-1">País</label>
            <select
              value={countryFilter}
              onChange={(e) => setCountryFilter(e.target.value)}
              className="input-glass text-sm py-2.5 bg-[#0a0f1e] text-gray-200"
            >
              <option value="all">Todos</option>
              {uniqueCountries.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>

          <div className="w-[100px] flex flex-col gap-1">
            <label className="text-[10px] uppercase tracking-widest font-bold text-gray-500 ml-1">Límite</label>
            <input
              type="number"
              value={limit}
              onChange={e => setLimit(parseInt(e.target.value) || 100)}
              className="input-glass text-sm py-2.5 text-center bg-[#ffffff05]"
            />
          </div>

          {(searchTerm || statusFilter !== 'all' || countryFilter !== 'all') && (
            <button
              onClick={() => { setSearchTerm(''); setStatusFilter('all'); setCountryFilter('all'); }}
              className="p-2.5 text-gray-400 hover:text-white hover:bg-white/5 rounded-xl transition"
              title="Limpiar filtros"
            >
              <X size={20} />
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500 text-sm font-medium flex items-center gap-3">
          <AlertCircle size={18} /> {error}
        </div>
      )}

      {/* Table Area */}
      {loading ? (
        <div className="flex justify-center py-20">
          <div className="w-10 h-10 border-4 border-cyan-500/30 border-t-cyan-500 rounded-full animate-spin" />
        </div>
      ) : (
        <div className="card-glass overflow-hidden">
          <div className="overflow-x-auto">
            <table className="table-glass">
              <thead>
                <tr>
                  <th className="w-24">ID</th>
                  <th>Estado</th>
                  <th>Ruta</th>
                  <th className="text-right">Monto Origen</th>
                  <th className="text-right">Payout</th>
                  <th className="text-right">Ganancia</th>
                  <th>Fecha</th>
                  <th className="text-center">Acción</th>
                </tr>
              </thead>
              <tbody>
                {filteredOrders.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-10 text-gray-500">
                      {orders.length === 0 ? 'No hay órdenes en la base de datos.' : 'Ninguna orden coincide con los filtros.'}
                    </td>
                  </tr>
                ) : (
                  filteredOrders.map((o: any) => (
                    <tr
                      key={o.public_id}
                      onClick={() => router.push(`/orders/${o.public_id}`)}
                      className="cursor-pointer group"
                    >
                      <td>
                        <span className="font-mono text-cyan-400 font-bold tracking-wider">#{o.public_id}</span>
                      </td>
                      <td>
                        <span className={cn(
                          "px-2.5 py-1 text-[11px] font-bold rounded-full border whitespace-nowrap",
                          statusStyles[o.status] || "bg-gray-500/10 text-gray-400 border-gray-500/30"
                        )}>
                          {statusLabels[o.status] || o.status}
                        </span>
                      </td>
                      <td>
                        <div className="font-medium text-sm text-gray-300">
                          {o.origin_country} <span className="text-gray-500 mx-1">→</span> {o.dest_country}
                        </div>
                      </td>
                      <td className="text-right font-semibold text-gray-200">
                        {formatCurrency(o.amount_origin, '')}
                      </td>
                      <td className="text-right font-semibold text-gray-200">
                        {formatCurrency(o.payout_dest, '')}
                      </td>
                      <td className="text-right">
                        {(o.profit_real_usdt || o.profit_usdt || 0) > 0 ? (
                          <div className="flex items-center justify-end gap-1.5 text-emerald-400">
                            <TrendingUp size={14} />
                            <span className="font-bold">${(o.profit_real_usdt || o.profit_usdt).toFixed(2)}</span>
                          </div>
                        ) : (
                          <span className="text-gray-500 font-medium">$0.00</span>
                        )}
                      </td>
                      <td>
                        <div className="flex flex-col">
                          <span className="text-sm text-gray-300">{formatDateTime(o.created_at).split(', ')[0]}</span>
                          <span className="text-[10px] text-gray-500">{formatDateTime(o.created_at).split(', ')[1]}</span>
                        </div>
                      </td>
                      <td className="text-center">
                        <button
                          className="p-1.5 text-gray-400 group-hover:text-cyan-400 group-hover:bg-cyan-500/10 rounded-lg transition-colors"
                          title="Ver detalle"
                          onClick={(e) => { e.stopPropagation(); router.push(`/orders/${o.public_id}`); }}
                        >
                          <Eye size={18} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
