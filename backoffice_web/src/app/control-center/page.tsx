'use client';

import React, { useEffect, useState } from 'react';
import SectionHeader from '@/components/ui/SectionHeader';
import MetricCard from '@/components/ui/MetricCard';
import DataTable from '@/components/ui/DataTable';
import LoadingState from '@/components/ui/LoadingState';
import MoneyCell from '@/components/ui/MoneyCell';
import CountryPill from '@/components/ui/CountryPill';
import RiskBadge from '@/components/ui/RiskBadge';
import { 
  TrendingUp, 
  ArrowRight, 
  AlertCircle,
  Database,
  Briefcase
} from 'lucide-react';
import api from '@/lib/api';
import { ApiEnvelope } from '@/types/common';
import { ExecutiveControlCenterData, ExecutiveRecentOrder, ExecutiveLeaderboardItem } from '@/types/executive';

export default function ControlCenter() {
  const [data, setData] = useState<ExecutiveControlCenterData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await api.get<ApiEnvelope<ExecutiveControlCenterData>>('/executive/control-center');
        if (res.data.ok) setData(res.data.data);
      } catch (err) {
        console.error('Error fetching control center data:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) return <LoadingState title="Cargando centro de mando ejecutivo..." />;

  const overview = data?.overview;
  const leaderboard = data?.leaderboard || [];
  const vault = data?.vault;
  const recent = data?.recent_activity || [];
  const risk = data?.risk_alerts;

  return (
    <div className="p-6 lg:p-10 space-y-10 animate-fade-in">
      <SectionHeader 
        title="Control Center" 
        subtitle="Visión estratégica 360° del ecosistema SendMax"
        rightSlot={
          <div className="flex items-center gap-2 px-4 py-2 bg-blue-500/10 rounded-full border border-blue-500/20">
            <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
            <span className="text-[10px] font-black text-blue-400 uppercase tracking-widest">Live Engine Active</span>
          </div>
        }
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard 
          label="Profit Real (PAGADAS)"
          value={<MoneyCell value={overview?.total_profit_real_usd || 0} />}
          trend={`${overview?.completed_orders || 0} Órdenes`}
          trendDirection="up"
          icon={<TrendingUp className="w-6 h-6" />}
        />
        <MetricCard 
          label="Bóveda Central"
          value={<MoneyCell value={vault?.vault_balance || 0} />}
          hint={`Total Profit: ${(vault?.total_profit || 0).toFixed(2)}`}
          icon={<Database className="w-6 h-6" />}
        />
        <MetricCard 
          label="Volumen Total USD"
          value={<MoneyCell value={overview?.total_volume_usd || 0} />}
          trendDirection="neutral"
          icon={<Briefcase className="w-6 h-6" />}
        />
        <MetricCard 
          label="Órdenes Pendientes"
          value={overview?.pending_orders || 0}
          trend={risk && risk.stuck_origin_verification_count > 0 ? `${risk.stuck_origin_verification_count} Estancadas` : 'Flujo normal'}
          trendDirection={risk && risk.stuck_origin_verification_count > 0 ? 'down' : 'up'}
          icon={<AlertCircle className="w-6 h-6" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <DataTable<ExecutiveRecentOrder> 
            title="Actividad Reciente"
            subtitle="Últimas 10 operaciones procesadas en tiempo real"
            columns={[
              { 
                key: 'public_id', 
                header: 'ID', 
                render: (r) => <span className="text-white/40 font-mono text-xs">{r.public_id}</span> 
              },
              { 
                key: 'route', 
                header: 'Ruta', 
                render: (r) => (
                  <div className="flex items-center gap-2">
                    <CountryPill country={r.origin_country} />
                    <ArrowRight size={10} className="text-white/20" />
                    <CountryPill country={r.dest_country} />
                  </div>
                )
              },
              { 
                key: 'amount_origin', 
                header: 'Monto', 
                render: (r) => <MoneyCell value={r.amount_origin} /> 
              },
              { 
                key: 'status', 
                header: 'Estado', 
                render: (r) => <RiskBadge level={r.status === 'PAGADA' ? 'low' : 'medium'} label={r.status} /> 
              }
            ]}
            data={recent}
            rowKey={(r) => r.public_id}
          />
        </div>

        <div className="space-y-6">
          <DataTable<ExecutiveLeaderboardItem> 
            title="Top Operadores"
            subtitle="Basado en Trust Score y Profit"
            columns={[
              { 
                key: 'alias', 
                header: 'Alias', 
                render: (r) => <span className="font-bold text-sm">{r.alias}</span> 
              },
              { 
                key: 'trust_score', 
                header: 'Score', 
                render: (r) => <span className="text-blue-400 font-black">{r.trust_score}</span> 
              }
            ]}
            data={leaderboard}
            rowKey={(r) => r.alias}
          />
        </div>
      </div>
    </div>
  );
}

