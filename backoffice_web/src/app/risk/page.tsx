'use client';

import React, { useEffect, useState } from 'react';
import SectionHeader from '@/components/ui/SectionHeader';
import MetricCard from '@/components/ui/MetricCard';
import DataTable from '@/components/ui/DataTable';
import LoadingState from '@/components/ui/LoadingState';
import RiskBadge from '@/components/ui/RiskBadge';
import MoneyCell from '@/components/ui/MoneyCell';
import StatCard from '@/components/ui/StatCard';
import { AlertTriangle, ShieldAlert, ZapOff } from 'lucide-react';
import api from '@/lib/api';

interface Anomaly {
  public_id: string;
  status: string;
  profit_usdt: number;
}

export default function RiskExecutive() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await api.get('/executive/risk');
        if (res.data.ok) setData(res.data.data);
      } catch (err) {
        console.error('Error fetching risk data:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) return <LoadingState title="Calculando vectores de riesgo operativo..." />;

  const stuck = data?.stuck_orders || {};
  const withdrawals = data?.pending_withdrawals || {};
  const anomalies: Anomaly[] = data?.anomalies || [];
  const health = data?.health_score || 0;

  return (
    <div className="p-6 lg:p-10 space-y-10 animate-fade-in">
      <SectionHeader 
        title="Riesgo Operativo" 
        subtitle="Monitor de anomalías, estancamiento y exposición financiera"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard 
          title="Health Score"
          value={`${health}%`}
          subtitle={health > 80 ? "Operativa Saludable" : "Alerta de Estancamiento"}
          accentClassName={health > 80 ? "from-green-600/10 to-emerald-500/5" : "from-red-600/10 to-orange-500/5"}
          icon={<ShieldAlert className={health > 80 ? "text-green-400" : "text-red-400"} />}
        />
        <MetricCard 
          label="Órdenes Estancadas"
          value={(stuck.stuck_origin_verification_count || 0) + (stuck.stuck_payment_proof_count || 0)}
          trend={`${stuck.stuck_origin_verification_count || 0} en Origen`}
          trendDirection="down"
          icon={<AlertTriangle className="text-orange-400" />}
        />
        <MetricCard 
          label="Retiros Pendientes"
          value={<MoneyCell value={withdrawals.amount || 0} />}
          hint={`${withdrawals.count || 0} Solicitudes`}
          icon={<ZapOff className="text-red-400" />}
        />
      </div>

      <div className="grid grid-cols-1 gap-8">
        <DataTable<Anomaly> 
          title="Anomalías y Alertas Recientes"
          subtitle="Métricas fuera de rango o patrones atípicos"
          columns={[
            { key: 'id', header: 'ID Orden', render: (a) => <span className="font-mono text-xs">{a.public_id}</span> },
            { key: 'status', header: 'Estado', render: (a) => <RiskBadge level={a.profit_usdt < 0 ? "critical" : "medium"} label={a.status} /> },
            { key: 'profit', header: 'Profit', render: (a) => (
              <span className={a.profit_usdt < 0 ? 'text-red-400 font-bold' : 'text-white/60'}>
                <MoneyCell value={a.profit_usdt} />
              </span>
            )},
            { key: 'action', header: 'Riesgo', render: (a) => (
              <span className="text-[10px] font-black uppercase text-red-500/60 tracking-wider">
                {a.profit_usdt < 0 ? 'Profit Negativo' : 'Consistencia Requerida'}
              </span>
            )}
          ]}
          data={anomalies}
          rowKey={(a) => a.public_id}
          emptyTitle="Sin anomalías críticas"
          emptyDescription="No se han detectado patrones de riesgo en las últimas 48 horas."
        />
      </div>
    </div>
  );
}
