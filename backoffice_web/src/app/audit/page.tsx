'use client';

import React, { useEffect, useState } from 'react';
import SectionHeader from '@/components/ui/SectionHeader';
import AuditFeed, { AuditFeedItem } from '@/components/ui/AuditFeed';
import LoadingState from '@/components/ui/LoadingState';
import api from '@/lib/api';

export default function AuditExecutive() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await api.get('/executive/audit');
        if (res.data.ok) setData(res.data.data);
      } catch (err) {
        console.error('Error fetching audit data:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) return <LoadingState title="Reconstruyendo feed de auditoría ejecutiva..." />;

  const feedRaw = data?.feed || [];
  const items: AuditFeedItem[] = feedRaw.map((e: any, idx: number) => ({
    id: idx,
    actor: e.actor || 'System',
    action: e.type || 'Event',
    target: e.detail || '',
    time: e.date
  }));

  return (
    <div className="p-6 lg:p-10 space-y-10 animate-fade-in">
      <SectionHeader 
        title="Auditoría y Trazabilidad" 
        subtitle="Registro histórico de acciones sensibles y eventos del sistema"
      />

      <div className="max-w-4xl mx-auto">
        <AuditFeed 
          items={items}
          title="Timeline Estratégico"
        />
      </div>
    </div>
  );
}
