'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { useAuth } from '@/components/AuthProvider';
import {
  Search,
  RefreshCcw,
  X,
  Eye,
  Shield,
  ShieldAlert,
  ToggleLeft,
  ToggleRight,
  AlertCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatCurrency, formatDateTime } from '@/lib/formatters';

interface User {
  id: number;
  telegram_user_id: number;
  alias: string;
  full_name: string | null;
  email: string | null;
  role: string;
  is_active: boolean;
  kyc_status: string;
  balance_usdt: string | null;
  total_orders: number;
  created_at: string;
}

const KYC_MAP: Record<string, { styles: string; label: string }> = {
  APPROVED: { styles: 'bg-[#10b9811a] text-[#10b981] border-[#10b9814d]', label: 'Aprobado' },
  SUBMITTED: { styles: 'bg-[#f59e0b1a] text-[#f59e0b] border-[#f59e0b4d]', label: 'Enviado' },
  REJECTED: { styles: 'bg-[#ef44441a] text-[#ef4444] border-[#ef44444d]', label: 'Rechazado' },
  PENDING: { styles: 'bg-gray-500/10 text-gray-400 border-gray-500/30', label: 'Pendiente' },
};

export default function UsersPage() {
  const { token } = useAuth();
  const router = useRouter();
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState('');
  const [activeSearch, setActiveSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchUsers = useCallback(async (q: string = '') => {
    setLoading(true);
    setError('');
    try {
      const query = q.trim() ? `?search=${encodeURIComponent(q.trim())}` : '';
      const res = await api.get<{ count: number; users: User[] }>(`/users${query}`);
      setUsers(res.data?.users || []);
      setActiveSearch(q.trim());
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Error cargando usuarios');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) fetchUsers();
  }, [token, fetchUsers]);

  const handleSearchChange = useCallback((value: string) => {
    setSearch(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchUsers(value), 400);
  }, [fetchUsers]);

  const handleClearSearch = useCallback(() => {
    setSearch('');
    setActiveSearch('');
    if (debounceRef.current) clearTimeout(debounceRef.current);
    fetchUsers();
  }, [fetchUsers]);

  const handleToggle = useCallback(async (userId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.put(`/users/${userId}/toggle`);
      await fetchUsers(activeSearch);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Error al cambiar estado');
    }
  }, [activeSearch, fetchUsers]);

  return (
    <div className="space-y-6 animate-fade-in">

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-black bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent tracking-tight">
            Usuarios
          </h1>
          <p className="text-sm font-medium text-gray-400 mt-1 flex items-center gap-2">
            {users.length} operadores y administradores
            {activeSearch && (
              <span className="px-2 py-0.5 rounded-md bg-white/10 text-white text-[11px] font-bold tracking-wider">
                Filtro: "{activeSearch}"
              </span>
            )}
          </p>
        </div>

        <button
          onClick={() => fetchUsers(activeSearch)}
          disabled={loading}
          className="flex items-center gap-2 px-5 py-2 rounded-xl border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500/20 transition-all text-sm font-bold disabled:opacity-50"
        >
          <RefreshCcw size={16} className={cn(loading && "animate-spin")} />
          Actualizar
        </button>
      </div>

      {/* Filters Card */}
      <div className="card-glass p-4 md:p-5">
        <div className="relative w-full md:w-[420px] text-gray-400 focus-within:text-cyan-400">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Buscar por alias, nombre o email..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="input-glass pl-10 pr-10 text-sm py-2.5 bg-[#ffffff05] w-full"
          />
          {search && (
            <button
              onClick={handleClearSearch}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-gray-500 hover:text-white rounded-lg transition"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500 text-sm font-medium flex items-center gap-3">
          <AlertCircle size={18} /> {error}
        </div>
      )}

      {/* Table */}
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
                  <th className="w-16">ID</th>
                  <th>Alias</th>
                  <th>Nombre</th>
                  <th>Telegram</th>
                  <th>Rol</th>
                  <th>KYC</th>
                  <th className="text-right">Balance</th>
                  <th className="text-right">Órdenes</th>
                  <th className="text-center">Estado</th>
                  <th className="text-center">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="text-center py-10 text-gray-500">
                      {activeSearch ? `Sin resultados para "${activeSearch}"` : 'No hay usuarios'}
                    </td>
                  </tr>
                ) : (
                  users.map((u) => {
                    const kyc = KYC_MAP[u.kyc_status] || KYC_MAP.PENDING;
                    return (
                      <tr
                        key={u.id}
                        onClick={() => router.push(`/users/${u.id}`)}
                        className="cursor-pointer group"
                      >
                        <td className="font-mono text-gray-400 font-bold">{u.id}</td>
                        <td className="font-bold text-gray-200">{u.alias}</td>
                        <td className="text-gray-300">{u.full_name || '-'}</td>
                        <td className="font-mono text-sm text-gray-400">{u.telegram_user_id || '-'}</td>
                        <td>
                          <span className={cn(
                            "flex items-center gap-1.5 w-fit px-2.5 py-1 text-[10px] font-black tracking-widest uppercase rounded",
                            u.role === 'admin' ? "bg-red-500/10 text-red-400 border border-red-500/20" : "bg-cyan-500/10 text-cyan-400 border border-cyan-500/20"
                          )}>
                            {u.role === 'admin' ? <ShieldAlert size={12} /> : <Shield size={12} />}
                            {u.role}
                          </span>
                        </td>
                        <td>
                          <span className={cn("px-2.5 py-1 text-[11px] font-bold rounded-full border whitespace-nowrap", kyc.styles)}>
                            {kyc.label}
                          </span>
                        </td>
                        <td className="text-right font-bold text-gray-200">
                          {formatCurrency(Number(u.balance_usdt || 0))}
                        </td>
                        <td className="text-right font-bold text-gray-400">
                          {u.total_orders || 0}
                        </td>
                        <td className="text-center">
                          <span className={cn(
                            "inline-flex items-center justify-center gap-1.5 px-2.5 py-1 text-[11px] font-bold rounded-lg border",
                            u.is_active ? "bg-[#10b9811a] text-[#10b981] border-[#10b98133]" : "bg-gray-500/10 text-gray-400 border-gray-500/30"
                          )}>
                            {u.is_active ? 'Activo' : 'Inactivo'}
                          </span>
                        </td>
                        <td className="text-center">
                          <div className="flex items-center justify-center gap-2">
                            <button
                              className="p-1.5 text-gray-400 hover:text-cyan-400 hover:bg-cyan-500/10 rounded-lg transition-colors"
                              title="Ver detalle"
                            >
                              <Eye size={18} />
                            </button>
                            <button
                              className={cn(
                                "p-1.5 rounded-lg transition-colors",
                                u.is_active ? "text-emerald-400 hover:bg-emerald-500/10" : "text-gray-500 hover:text-yellow-400 hover:bg-yellow-500/10"
                              )}
                              title={u.is_active ? 'Desactivar' : 'Activar'}
                              onClick={(e) => handleToggle(u.id, e)}
                            >
                              {u.is_active ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
