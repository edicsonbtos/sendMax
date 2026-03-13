'use client';

import React, { useEffect, useState } from 'react';
import SectionHeader from '@/components/ui/SectionHeader';
import MetricCard from '@/components/ui/MetricCard';
import DataTable from '@/components/ui/DataTable';
import LoadingState from '@/components/ui/LoadingState';
import MoneyCell from '@/components/ui/MoneyCell';
import CountryPill from '@/components/ui/CountryPill';
import EmptyState from '@/components/ui/EmptyState';
import { Landmark, Globe } from 'lucide-react';
import api from '@/lib/api';

interface Balance {
  origin_country: string;
  fiat_currency: string;
  current_balance: number;
}

interface CountrySummary {
  country: string;
  total_balance_usd: number;
  currencies: string[];
}

export default function Treasury() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await api.get('/executive/treasury');
        if (res.data.ok) setData(res.data.data);
      } catch (err) {
        console.error('Error fetching treasury data:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) return <LoadingState title="Consolidando balances de tesorería..." />;

  const byCountry: CountrySummary[] = data?.by_country || [];
  const balances: Balance[] = data?.balances || [];

  if (balances.length === 0) {
    return (
      <div className="p-10">
        <EmptyState 
          title="Sin datos de tesorería" 
          description="Debes registrar cierres de origin o sweeps para ver balances netos." 
        />
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-10 space-y-10 animate-fade-in">
      <SectionHeader 
        title="Tesorería Corporativa" 
        subtitle="Consolidación de liquidez en países de captación"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {byCountry.slice(0, 3).map((c) => (
          <MetricCard 
            key={c.country}
            label={`Balance en ${c.country}`}
            value={<MoneyCell value={c.total_balance_usd} />}
            hint={`${c.currencies.length} Monedas activas`}
            icon={<Landmark className="w-6 h-6" />}
          />
        ))}
      </div>

      <DataTable<Balance> 
        title="Balances Detallados por Moneda"
        subtitle="Cálculo neto de Entradas - Salidas (Sweeps)"
        columns={[
          { 
            key: 'country', 
            header: 'País', 
            render: (r) => <CountryPill country={r.origin_country} /> 
          },
          { 
            key: 'currency', 
            header: 'Moneda', 
            render: (r) => <span className="font-bold">{r.fiat_currency}</span> 
          },
          { 
            key: 'balance', 
            header: 'Balance Líquido', 
            render: (r) => <MoneyCell value={r.current_balance} /> 
          }
        ]}
        data={balances}
        rowKey={(r) => `${r.origin_country}-${r.fiat_currency}`}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="p-8 bg-gradient-to-br from-blue-600/10 to-cyan-500/5 rounded-3xl border border-blue-500/10 space-y-4">
          <div className="h-12 w-12 rounded-2xl bg-blue-500/20 flex items-center justify-center text-blue-400">
            <Globe size={24} />
          </div>
          <h4 className="text-xl font-black text-white tracking-tight">Estrategia de Fondos</h4>
          <p className="text-sm text-white/40 font-medium leading-relaxed">
            Los balances mostrados aquí son netos de captación en los países de origen. 
          </p>
        </div>
      </div>
    </div>
  );
}
