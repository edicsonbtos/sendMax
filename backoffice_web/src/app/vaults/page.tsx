'use client';

import React, { useEffect, useState } from 'react';
import SectionHeader from '@/components/ui/SectionHeader';
import MetricCard from '@/components/ui/MetricCard';
import VaultSummaryCard from '@/components/ui/VaultSummaryCard';
import DataTable from '@/components/ui/DataTable';
import LoadingState from '@/components/ui/LoadingState';
import MoneyCell from '@/components/ui/MoneyCell';
import api from '@/lib/api';
import { Database, ShieldCheck, Zap } from 'lucide-react';
import { ApiEnvelope } from '@/types/common';
import { ExecutiveVaultRow, ExecutiveVaultMetrics } from '@/types/executive';

interface VaultsData {
  central_vault: ExecutiveVaultMetrics;
  radar: any;
  vaults: ExecutiveVaultRow[];
}

export default function VaultsExecutive() {
  const [data, setData] = useState<VaultsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await api.get<ApiEnvelope<VaultsData>>('/executive/vaults');
        if (res.data.ok) setData(res.data.data);
      } catch (err) {
        console.error('Error fetching vaults data:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) return <LoadingState title="Escaneando radar de liquidez..." />;

  const central = data?.central_vault;
  const radar = data?.radar || {};
  const vaults = data?.vaults || [];

  return (
    <div className="p-6 lg:p-10 space-y-10 animate-fade-in">
      <SectionHeader 
        title="Bóvedas y Liquidez" 
        subtitle="Control central de activos en custodia y wallets operativas"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard 
          label="Bóveda Central Líquida"
          value={<MoneyCell value={central?.vault_balance || 0} />}
          hint="Profit Neto disponible"
          icon={<ShieldCheck className="w-6 h-6" />}
          trendDirection="up"
        />
        <MetricCard 
          label="Custodia Digital"
          value={<MoneyCell value={radar.by_type?.digital?.total || 0} />}
          hint={`${radar.by_type?.digital?.count || 0} Cuentas`}
          icon={<Database className="w-6 h-6 text-blue-400" />}
        />
        <MetricCard 
          label="Cripto / Stablecoins"
          value={<MoneyCell value={radar.by_type?.crypto?.total || 0} />}
          hint={`${radar.by_type?.crypto?.count || 0} Wallets`}
          icon={<Zap className="w-6 h-6 text-cyan-400" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {vaults.slice(0, 4).map((v) => (
          <VaultSummaryCard 
            key={v.id}
            title={v.name}
            balance={v.balance}
            currency={v.currency}
            risk={v.balance < 500 ? "medium" : "low"}
            subtitle={v.provider}
          />
        ))}
      </div>

      <DataTable<ExecutiveVaultRow> 
        title="Detalle de Bóvedas Activas"
        subtitle="Desglose por proveedor y tipo de custodia"
        columns={[
          { key: 'name', header: 'Nombre', render: (v) => <span className="font-bold">{v.name}</span> },
          { key: 'provider', header: 'Proveedor', render: (v) => <span className="text-white/40">{v.provider || 'N/A'}</span> },
          { key: 'type', header: 'Tipo', render: (v) => <span className="text-xs uppercase font-black text-blue-400">{v.type}</span> },
          { key: 'balance', header: 'Balance', render: (v) => <MoneyCell value={v.balance} /> }
        ]}
        data={vaults}
        rowKey={(v) => v.id.toString()}
      />
    </div>
  );
}

