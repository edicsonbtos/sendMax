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
import { cn } from '@/lib/cn';
import { formatCurrency } from '@/lib/formatters';

// UI Components
import SectionHeader from '@/components/ui/SectionHeader';
import FilterBar from '@/components/ui/FilterBar';
import Input from '@/components/ui/Input';
import Button from '@/components/ui/Button';
import LoadingState from '@/components/ui/LoadingState';
import EmptyState from '@/components/ui/EmptyState';
import DataTable, { DataTableColumn } from '@/components/ui/DataTable';
import Badge from '@/components/ui/Badge';

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

const KYC_MAP: Record<string, { color: 'success' | 'warning' | 'danger' | 'default'; label: string }> = {
  APPROVED: { color: 'success', label: 'Aprobado' },
  SUBMITTED: { color: 'warning', label: 'Enviado' },
  REJECTED: { color: 'danger', label: 'Rechazado' },
  PENDING: { color: 'default', label: 'Pendiente' },
};

export default function UsersPage() {
  const { token, isReady } = useAuth();
  const router = useRouter();
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState('');
  const [activeSearch, setActiveSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchUsers = useCallback(async (q: string = '') => {
    if (!token) return;
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
  }, [token]);

  useEffect(() => {
    if (isReady && token) fetchUsers();
  }, [isReady, token, fetchUsers]);

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

  const columns: DataTableColumn<User>[] = [
    {
      key: 'id',
      header: 'ID',
      className: 'w-16 font-mono text-gray-400 font-bold',
      render: (u) => u.id
    },
    {
      key: 'alias',
      header: 'Usuario',
      className: 'font-bold text-gray-200',
      render: (u) => (
        <div>
          <div>{u.alias}</div>
          <div className="text-[10px] text-gray-500 font-mono">TG: {u.telegram_user_id || '-'}</div>
        </div>
      )
    },
    {
      key: 'full_name',
      header: 'Nombre Completo',
      render: (u) => u.full_name || '-'
    },
    {
      key: 'role',
      header: 'Rol',
      render: (u) => (
        <Badge color={u.role === 'admin' ? 'danger' : 'info'}>
          <div className="flex items-center gap-1.5 uppercase tracking-widest text-[10px]">
            {u.role === 'admin' ? <ShieldAlert size={12} /> : <Shield size={12} />}
            {u.role}
          </div>
        </Badge>
      )
    },
    {
      key: 'kyc_status',
      header: 'KYC',
      render: (u) => {
        const kyc = KYC_MAP[u.kyc_status] || KYC_MAP.PENDING;
        return <Badge color={kyc.color}>{kyc.label}</Badge>;
      }
    },
    {
      key: 'balance',
      header: 'Balance',
      className: 'text-right font-bold text-gray-200',
      render: (u) => formatCurrency(Number(u.balance_usdt || 0))
    },
    {
      key: 'status',
      header: 'Estado',
      className: 'text-center',
      render: (u) => (
        <Badge color={u.is_active ? 'success' : 'default'}>
          {u.is_active ? 'Activo' : 'Inactivo'}
        </Badge>
      )
    },
    {
      key: 'actions',
      header: 'Acciones',
      className: 'text-center',
      render: (u) => (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              router.push(`/users/${u.id}`);
            }}
            className="p-1.5 text-gray-400 hover:text-cyan-400"
            title="Ver detalle"
          >
            <Eye size={18} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => handleToggle(u.id, e)}
            className={cn(
              "p-1.5",
              u.is_active ? "text-emerald-400" : "text-gray-500 hover:text-yellow-400"
            )}
            title={u.is_active ? 'Desactivar' : 'Activar'}
          >
            {u.is_active ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
          </Button>
        </div>
      )
    }
  ];

  if (!isReady || !token) return null;

  return (
    <div className="space-y-6 animate-fade-in pb-10">
      <SectionHeader
        title="Usuarios"
        subtitle={`${users.length} operadores y administradores gestionados`}
        rightSlot={
          <Button
            variant="primary"
            icon={<RefreshCcw size={16} className={cn(loading && "animate-spin")} />}
            onClick={() => fetchUsers(activeSearch)}
            loading={loading}
          >
            Actualizar
          </Button>
        }
      />

      <FilterBar>
        <div className="relative flex-1 max-w-md">
          <Input
            placeholder="Buscar por alias, nombre o email..."
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            icon={<Search size={18} />}
          />
          {search && (
            <button
              onClick={handleClearSearch}
              className="absolute right-3 top-10 p-1.5 text-gray-500 hover:text-white rounded-lg transition"
            >
              <X size={16} />
            </button>
          )}
        </div>
      </FilterBar>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-500 text-sm font-medium flex items-center gap-3">
          <AlertCircle size={18} /> {error}
        </div>
      )}

      {loading && users.length === 0 ? (
        <LoadingState title="Consultando base de usuarios..." />
      ) : users.length === 0 ? (
        <EmptyState
          title={activeSearch ? `Sin resultados para "${activeSearch}"` : "No hay usuarios registrados"}
          description="Ajusta los filtros de búsqueda o verifica la conexión con el servidor."
          action={
            <Button variant="secondary" onClick={handleClearSearch}>
              Limpiar búsqueda
            </Button>
          }
        />
      ) : (
        <DataTable
          columns={columns}
          data={users}
          loading={loading}
          rowKey={(u) => u.id}
          className="animate-slide-up"
        />
      )}
    </div>
  );
}
