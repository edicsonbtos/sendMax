'use client';

import React, { useEffect, useState } from 'react';
import SectionHeader from '@/components/ui/SectionHeader';
import MetricCard from '@/components/ui/MetricCard';
import DataTable from '@/components/ui/DataTable';
import LoadingState from '@/components/ui/LoadingState';
import RiskBadge from '@/components/ui/RiskBadge';
import MoneyCell from '@/components/ui/MoneyCell';
import StatCard from '@/components/ui/StatCard';
import { AlertTriangle, ShieldAlert, ZapOff, Fingerprint, Database } from 'lucide-react';
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

  if (loading) return <LoadingState title="Calculando vectores de riesgo operativo e integridad..." />;

  const stuck = data?.stuck_orders || {};
  const withdrawals = data?.pending_withdrawals || {};
  const anomalies: Anomaly[] = data?.anomalies || [];
  const integrity = data?.integrity || {};
  const health = data?.health_score || 0;

  return (
    <div className="p-6 lg:p-10 space-y-10 animate-fade-in">
      <SectionHeader 
        title="Riesgo e Integridad" 
        subtitle="Monitor de anomalías, integridad del ledger y exposición financiera"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard 
          title="Health Score"
          value={`${health}%`}
          subtitle={health > 80 ? "Operativa Saludable" : "Alerta de Integridad"}
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
          label="Liquidez Estacionada"
          value={integrity.stagnant_liquidity?.length || 0}
          hint="Países sin sweep > 48h"
          icon={<Database className="text-blue-400" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/5 space-y-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
              <Fingerprint size={20} />
            </div>
            <div>
              <h3 className="text-sm font-black text-white uppercase tracking-widest">Integridad Ledger</h3>
              <p className="text-[10px] text-white/40 font-bold uppercase tracking-wider">Lectura de consistencia transaccional</p>
            </div>
          </div>

          <div className="space-y-3">
            {integrity.ledger_anomalies?.length === 0 ? (
              <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/10">
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <p className="text-xs font-bold text-emerald-300">No se detectan discrepancias en balances del ledger.</p>
              </div>
            ) : (
              integrity.ledger_anomalies?.map((a: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-4 rounded-xl bg-red-500/5 border border-red-500/10">
                  <p className="text-xs font-bold text-red-300 uppercase tracking-tighter">Wallet ID: {a.wallet_id}</p>
                  <p className="text-xs font-black text-red-400"><MoneyCell value={a.balance} /></p>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/5 space-y-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-500/10 text-red-400">
              <ZapOff size={20} />
            </div>
            <div>
              <h3 className="text-sm font-black text-white uppercase tracking-widest">Retiros Pendientes</h3>
              <p className="text-[10px] text-white/40 font-bold uppercase tracking-wider">Exposición de salida inmediata</p>
            </div>
          </div>

          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-black text-white"><MoneyCell value={withdrawals.amount} /></span>
            <span className="text-xs font-bold text-white/40 uppercase tracking-widest">{withdrawals.count} Solicitudes</span>
          </div>
        </div>
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
