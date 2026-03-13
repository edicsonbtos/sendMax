'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';
import api from '@/lib/api';
import { cn } from '@/lib/cn';

// UI Components
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import SectionHeader from '@/components/ui/SectionHeader';
import Badge from '@/components/ui/Badge';
import LoadingState from '@/components/ui/LoadingState';
import MetricCard from '@/components/ui/MetricCard';

// Icons
import { 
  ArrowLeft, 
  User, 
  Mail, 
  Shield, 
  Activity, 
  Calendar,
  Wallet,
  ArrowUpRight,
  Lock,
  UserX,
  UserCheck
} from 'lucide-react';

interface UserDetail {
  id: number;
  telegram_user_id: number;
  alias: string;
  full_name: string | null;
  email: string | null;
  role: string;
  is_active: boolean;
  kyc_status: string;
  balance_usdt: string;
  total_orders: number;
  created_at: string;
}

export default function UserDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { token, isReady } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [user, setUser] = useState<UserDetail | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<UserDetail>(`/users/${id}`);
      setUser(res.data);
    } catch (e: any) {
      setError('Error cargando usuario');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (isReady && token && id) load();
  }, [isReady, token, id, load]);

  const handleToggleActive = async () => {
    try {
      await api.put(`/users/${id}/toggle`);
      load();
    } catch (e: any) {
      alert('Error al cambiar estado');
    }
  };

  if (!isReady || !token) return null;
  if (loading) return <LoadingState title="Consultando perfil..." />;
  if (!user) return <div className="p-8 text-rose-500 font-bold bg-rose-500/10 rounded-2xl">Usuario no encontrado</div>;

  return (
    <div className="space-y-8 pb-10">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => router.back()} icon={<ArrowLeft size={20} />} />
        <div className="flex flex-col">
          <h1 className="text-2xl font-black text-white">{user.alias}</h1>
          <div className="flex gap-2 mt-1">
             <Badge color={user.role === 'admin' ? 'danger' : 'info'}>{user.role.toUpperCase()}</Badge>
             <Badge color={user.is_active ? 'success' : 'warning'}>{user.is_active ? 'ACTIVO' : 'INACTIVO'}</Badge>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Profile Card */}
        <Card className="p-8 flex flex-col items-center text-center">
           <div className={cn(
             "w-24 h-24 rounded-full flex items-center justify-center mb-6",
             user.role === 'admin' ? "bg-rose-500/20 text-rose-500" : "bg-blue-500/20 text-blue-500"
           )}>
             <User size={48} />
           </div>
           
           <h2 className="text-xl font-black text-white mb-1">{user.full_name || user.alias}</h2>
           <p className="text-sm text-gray-500 mb-6">@{user.alias}</p>
           
           <div className="w-full space-y-3">
             <Button 
                variant="secondary" 
                className="w-full" 
                icon={<Lock size={16} />} 
                onClick={() => {}}
             >
               Reset Password
             </Button>
             <Button 
                variant={user.is_active ? "ghost" : "primary"} 
                className={cn("w-full", user.is_active ? "text-rose-500 hover:bg-rose-500/10" : "")} 
                icon={user.is_active ? <UserX size={16} /> : <UserCheck size={16} />}
                onClick={handleToggleActive}
             >
               {user.is_active ? 'Desactivar Cuenta' : 'Activar Cuenta'}
             </Button>
           </div>
        </Card>

        {/* Stats & Details */}
        <div className="lg:col-span-2 space-y-8">
           <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <MetricCard
                label="Balance USDT"
                value={`$${parseFloat(user.balance_usdt).toFixed(2)}`}
                icon={<Wallet size={24} />}
                hint="Fondos líquidos disponibles"
              />
              <MetricCard
                label="Órdenes Totales"
                value={user.total_orders.toString()}
                icon={<Activity size={24} />}
                hint="Procesadas históricamente"
              />
           </div>

           <Card className="p-6">
              <h3 className="text-sm font-bold text-gray-400 mb-6 uppercase tracking-widest">Información de Cuenta</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                 <div className="space-y-1">
                   <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Telegram ID</p>
                   <p className="text-white font-bold font-mono">{user.telegram_user_id}</p>
                 </div>
                 <div className="space-y-1">
                   <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Email</p>
                   <p className="text-white font-bold">{user.email || 'No configurado'}</p>
                 </div>
                 <div className="space-y-1">
                   <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest">KYC Status</p>
                   <Badge color={user.kyc_status === 'VERIFIED' ? 'success' : 'warning'}>{user.kyc_status}</Badge>
                 </div>
                 <div className="space-y-1">
                   <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Miembro desde</p>
                   <div className="flex items-center gap-2 text-white font-medium">
                     <Calendar size={14} className="text-gray-500" /> {new Date(user.created_at).toLocaleDateString()}
                   </div>
                 </div>
              </div>
           </Card>
        </div>
      </div>
    </div>
  );
}