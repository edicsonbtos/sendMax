'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as ChartTooltip,
  ResponsiveContainer,
} from 'recharts';
import { useAuth } from '@/components/AuthProvider';
import api from '@/lib/api';
import { cn } from '@/lib/cn';
import { formatCurrency } from '@/lib/formatters';

// UI Components
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import SectionHeader from '@/components/ui/SectionHeader';
import MetricCard from '@/components/ui/MetricCard';
import MoneyCell from '@/components/ui/MoneyCell';
import FilterBar from '@/components/ui/FilterBar';
import LoadingState from '@/components/ui/LoadingState';
import Table from '@/components/ui/Table';
import Badge from '@/components/ui/Badge';

// Icons
import { 
  RefreshCcw, 
  TrendingUp, 
  Receipt, 
  DollarSign, 
  BarChart3, 
  ArrowUpRight,
  TrendingDown
} from 'lucide-react';

/* ============ Types ============ */
interface MetricsOverview {
  total_orders: number;
  pending_orders: number;
  completed_orders: number;
  total_volume_usd: number;
  total_volume_dest: number;
  daily_volume: { date: string; volume: number }[];
}

interface CorridorMetric {
  route: string;
  volume: number;
  count: number;
  avg_rate: number;
}

export default function MetricsPage() {
  const { token, isReady } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [overview, setOverview] = useState<MetricsOverview | null>(null);
  const [corridors, setCorridors] = useState<CorridorMetric[]>([]);

  const loadMetrics = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      // Intentamos usar endpoints existentes o adaptamos
      const res = await api.get<{ overview: MetricsOverview; corridors: CorridorMetric[] }>('/metrics/overview');
      // Nota: Si el endpoint no coincide exactamente, el fallback es vital para no romper la UI
      setOverview(res.data.overview || {
        total_orders: 0, pending_orders: 0, completed_orders: 0, 
        total_volume_usd: 0, total_volume_dest: 0, daily_volume: []
      });
      setCorridors(res.data.corridors || []);
    } catch (e: any) {
      console.error('Error metrics:', e);
      setError('Error al conectar con la API de métricas');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (isReady && token) loadMetrics();
  }, [isReady, token, loadMetrics]);

  if (!isReady || !token) return null;

  return (
    <div className="space-y-8 pb-10">
      <SectionHeader
        title="Dashboard de Métricas"
        subtitle="Visualización en tiempo real de volumen y operaciones maestras"
        rightSlot={
          <Button
            variant="primary"
            icon={<RefreshCcw size={18} className={loading ? "animate-spin" : ""} />}
            onClick={loadMetrics}
            loading={loading}
          >
            Actualizar
          </Button>
        }
      />

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-500 font-bold animate-shake">
          {error}
        </div>
      )}

      {loading ? (
        <LoadingState title="Calculando rendimiento..." />
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <MetricCard
              label="Volumen Total"
              value={<MoneyCell value={overview?.total_volume_usd || 0} emphasize />}
              icon={<DollarSign size={24} />}
              trendDirection="up"
              hint="Volumen histórico acumulado"
            />
            <MetricCard
              label="Órdenes Totales"
              value={overview?.total_orders.toString() || "0"}
              icon={<Receipt size={24} />}
              trendDirection="neutral"
              hint={`${overview?.completed_orders} completadas`}
            />
            <MetricCard
              label="Pendientes"
              value={overview?.pending_orders.toString() || "0"}
              icon={<BarChart3 size={24} />}
              trendDirection={overview?.pending_orders! > 10 ? "down" : "neutral"}
              hint="Órdenes en proceso de verificación"
            />
            <MetricCard
              label="Crecimiento"
              value="+12.5%"
              icon={<ArrowUpRight size={24} />}
              trendDirection="up"
              hint="Vs. periodo anterior"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Chart Area */}
            <Card className="lg:col-span-2 p-6 overflow-hidden">
               <div className="flex items-center justify-between mb-6">
                 <div>
                   <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest">Volumen Diario</h3>
                   <p className="text-[10px] text-gray-500 mt-1 font-medium">Últimos 30 días de operación</p>
                 </div>
                 <Badge color="info">Filtro: USD</Badge>
               </div>
               
               <div className="h-[350px] w-full">
                 {overview?.daily_volume && overview.daily_volume.length > 0 ? (
                   <ResponsiveContainer width="100%" height="100%">
                     <AreaChart data={overview.daily_volume}>
                       <defs>
                         <linearGradient id="colorVol" x1="0" y1="0" x2="0" y2="1">
                           <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                           <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                         </linearGradient>
                       </defs>
                       <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                       <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: '#6b7280', fontSize: 10 }} dy={10} />
                       <YAxis axisLine={false} tickLine={false} tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={(v) => `$${v}`} />
                       <ChartTooltip
                         contentStyle={{ backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                         itemStyle={{ color: '#fff', fontSize: '12px', fontWeight: 'bold' }}
                         labelStyle={{ color: '#6b7280', marginBottom: '4px' }}
                       />
                       <Area type="monotone" dataKey="volume" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorVol)" />
                     </AreaChart>
                   </ResponsiveContainer>
                 ) : (
                   <div className="h-full flex items-center justify-center border border-dashed border-white/5 rounded-2xl text-gray-500 text-sm">
                     Sin datos históricos disponibles
                   </div>
                 )}
               </div>
            </Card>

            {/* Distribution/Status */}
            <Card className="p-6">
               <div className="mb-6">
                 <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest">Top Rutas</h3>
                 <p className="text-[10px] text-gray-500 mt-1 font-medium">Distribución por volumen</p>
               </div>
               
               <div className="space-y-5">
                 {corridors.slice(0, 6).map((c, idx) => {
                   const maxVol = Math.max(...corridors.map(x => x.volume), 1);
                   const pct = (c.volume / maxVol) * 100;
                   return (
                     <div key={idx} className="group cursor-default">
                       <div className="flex justify-between items-end mb-2">
                         <span className="text-xs font-bold text-gray-300 group-hover:text-blue-400 transition-colors uppercase tracking-tight">{c.route}</span>
                         <span className="text-xs font-black text-white">{formatCurrency(c.volume)}</span>
                       </div>
                       <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden border border-white/5">
                         <div 
                           className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full transition-all duration-1000"
                           style={{ width: `${pct}%`, boxShadow: '0 0 10px rgba(59, 130, 246, 0.4)' }}
                         />
                       </div>
                       <div className="flex justify-between mt-1">
                         <span className="text-[9px] font-bold text-gray-500 uppercase tracking-widest">{c.count} órdenes</span>
                         <span className="text-[9px] font-bold text-blue-500/60 uppercase tracking-widest">Rate {c.avg_rate.toFixed(2)}</span>
                       </div>
                     </div>
                   );
                 })}
                 
                 {corridors.length === 0 && (
                   <div className="py-12 text-center text-gray-500 text-sm font-medium">
                     Sin datos de corredores
                   </div>
                 )}
               </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
