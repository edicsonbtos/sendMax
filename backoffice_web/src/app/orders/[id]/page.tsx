'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@/components/AuthProvider';
import api from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatCurrency } from '@/lib/formatters';

// UI Components
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import SectionHeader from '@/components/ui/SectionHeader';
import Badge from '@/components/ui/Badge';
import LoadingState from '@/components/ui/LoadingState';
import Input from '@/components/ui/Input';

// Icons
import { 
  ArrowLeft, 
  Receipt, 
  Globe, 
  Calendar, 
  DollarSign, 
  User, 
  FileText,
  ExternalLink,
  AlertCircle
} from 'lucide-react';

interface OrderDetail {
  id: number;
  public_id: number;
  operator_alias: string;
  origin_country: string;
  dest_country: string;
  amount_origin: number;
  rate_client: number;
  payout_dest: number;
  beneficiary_text: string;
  status: string;
  created_at: string;
  origin_payment_proof_file_id: string | null;
  dest_payment_proof_file_id: string | null;
  profit_usdt: number | null;
}

export default function OrderDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const { token, isReady } = useAuth();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [order, setOrder] = useState<OrderDetail | null>(null);
  
  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<OrderDetail>(`/orders/${id}`);
      setOrder(res.data);
    } catch (e: any) {
      setError('No se pudo cargar el detalle de la orden');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (isReady && token && id) load();
  }, [isReady, token, id, load]);

  if (!isReady || !token) return null;
  if (loading) return <LoadingState title="Cargando detalles de orden..." />;
  if (!order) return (
    <div className="p-8 text-center text-rose-500 font-bold bg-rose-500/10 border border-rose-500/20 rounded-2xl">
      <AlertCircle className="mx-auto mb-2" /> Orden no encontrada
    </div>
  );

  const statusColors: Record<string, "success" | "warning" | "danger" | "info"> = {
    PAGADA: "success",
    COMPLETADA: "success",
    CANCELADA: "danger",
    CREADA: "info",
    EN_PROCESO: "warning"
  };

  return (
    <div className="space-y-8 pb-10">
      <div className="flex items-center gap-4">
        <Button variant="ghost" onClick={() => router.back()} icon={<ArrowLeft size={20} />} />
        <div className="flex flex-col">
          <h1 className="text-2xl font-black text-white">Orden #{order.public_id}</h1>
          <div className="mt-1">
             <Badge color={statusColors[order.status] || "warning"}>{order.status}</Badge>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Details */}
        <div className="lg:col-span-2 space-y-8">
          <Card className="p-6">
            <div className="flex items-center gap-2 mb-6 text-[10px] font-bold text-gray-500 uppercase tracking-widest">
              <Receipt size={14} /> Detalles de Operación
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-y-8 gap-x-12">
              <div className="space-y-1">
                <span className="text-[10px] font-black text-gray-500 uppercase tracking-wider">Ruta Maestro</span>
                <div className="flex items-center gap-2 text-white font-bold">
                  <Globe size={16} className="text-blue-500" /> {order.origin_country} → {order.dest_country}
                </div>
              </div>
              
              <div className="space-y-1">
                <span className="text-[10px] font-black text-gray-500 uppercase tracking-wider">Fecha de Registro</span>
                <div className="flex items-center gap-2 text-white font-medium">
                  <Calendar size={16} className="text-gray-400" /> {new Date(order.created_at).toLocaleString()}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[10px] font-black text-gray-500 uppercase tracking-wider">Monto Origen</span>
                <div className="text-2xl font-black text-blue-400">
                   {formatCurrency(order.amount_origin)}
                </div>
              </div>

              <div className="space-y-1">
                <span className="text-[10px] font-black text-gray-500 uppercase tracking-wider">Tasa Aplicada</span>
                <div className="text-xl font-bold text-white">
                   {order.rate_client.toLocaleString()}
                </div>
              </div>

              <div className="space-y-1 pt-4 border-t border-white/5">
                <span className="text-[10px] font-black text-gray-500 uppercase tracking-wider">Total Desembolso</span>
                <div className="text-2xl font-black text-emerald-400">
                   {formatCurrency(order.payout_dest)}
                </div>
              </div>

              <div className="space-y-1 pt-4 border-t border-white/5">
                <span className="text-[10px] font-black text-gray-500 uppercase tracking-wider">Operador Responsable</span>
                <div className="flex items-center gap-2 text-white font-bold">
                  <User size={16} className="text-purple-400" /> @{order.operator_alias}
                </div>
              </div>
            </div>
          </Card>

          <Card className="p-6">
            <div className="flex items-center gap-2 mb-6 text-[10px] font-bold text-gray-500 uppercase tracking-widest">
              <FileText size={14} /> Datos de Beneficiario
            </div>
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6 font-mono text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">
              {order.beneficiary_text}
            </div>
          </Card>
        </div>

        {/* Sidebar Info */}
        <div className="space-y-8">
           <Card className="p-6 bg-blue-600/10 border-blue-500/20 shadow-blue-900/10">
              <div className="flex justify-between items-center mb-6">
                <span className="text-[10px] font-black text-blue-400 uppercase tracking-widest">Profit Generado</span>
              </div>
              <div className="text-4xl font-black text-white mb-2">
                ${order.profit_usdt?.toFixed(2) || '0.00'}
              </div>
              <p className="text-[11px] text-blue-300/60 font-medium">Margen neto estimado en USDT</p>
           </Card>

           <Card className="p-6">
             <h3 className="text-sm font-bold text-gray-400 mb-6 uppercase tracking-widest">Comprobantes</h3>
             <div className="space-y-3">
               <Button 
                variant="secondary" 
                className="w-full" 
                icon={<ExternalLink size={14} />}
                disabled={!order.origin_payment_proof_file_id}
                onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/admin/media/${order.origin_payment_proof_file_id}`, '_blank')}
               >
                 Ver Origen
               </Button>
               <Button 
                variant="secondary" 
                className="w-full" 
                icon={<ExternalLink size={14} />}
                disabled={!order.dest_payment_proof_file_id}
                onClick={() => window.open(`${process.env.NEXT_PUBLIC_API_URL}/admin/media/${order.dest_payment_proof_file_id}`, '_blank')}
               >
                 Ver Destino
               </Button>
             </div>
           </Card>
        </div>
      </div>
    </div>
  );
}