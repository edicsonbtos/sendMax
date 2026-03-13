'use client';

import React, { useEffect, useState } from 'react';
import SectionHeader from '@/components/ui/SectionHeader';
import AuditFeed, { AuditFeedItem } from '@/components/ui/AuditFeed';
import LoadingState from '@/components/ui/LoadingState';
import api from '@/lib/api';
import { cn } from '@/lib/cn';

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

  if (loading) return <LoadingState title="Reconstruyendo trazabilidad ejecutiva de red..." />;

  const feedRaw = data?.feed || [];
  
  // Enriquecemos los items del feed con severidad visual
  const items: (AuditFeedItem & { severity?: string })[] = feedRaw.map((e: any, idx: number) => ({
    id: idx,
    actor: e.actor || 'System',
    action: e.type || 'Event',
    target: e.detail || '',
    time: e.date,
    severity: e.severity || 'INFO'
  }));

  return (
    <div className="p-6 lg:p-10 space-y-10 animate-fade-in">
      <SectionHeader 
        title="Auditoría y Trazabilidad" 
        subtitle="Registro histórico de acciones sensibles, retiros y eventos del core"
      />

      <div className="max-w-5xl mx-auto space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5">
            <p className="text-[10px] font-black text-white/40 uppercase tracking-widest">Eventos Totales</p>
            <p className="text-2xl font-black text-white mt-1">{items.length}</p>
          </div>
          <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5">
            <p className="text-[10px] font-black text-amber-400/40 uppercase tracking-widest">Warnings Recientes</p>
            <p className="text-2xl font-black text-amber-400 mt-1">{items.filter(i => i.severity === 'WARNING').length}</p>
          </div>
          <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/5">
            <p className="text-[10px] font-black text-cyan-400/40 uppercase tracking-widest">Último Evento</p>
            <p className="text-sm font-bold text-white mt-2 truncate">{items[0]?.action || 'N/A'}</p>
          </div>
        </div>

        <div className="relative">
          <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-gradient-to-b from-blue-500/20 via-white/5 to-transparent hidden sm:block" />
          
          <div className="space-y-6">
            {items.map((item) => (
              <div key={item.id} className="relative pl-0 sm:pl-16 group">
                {/* Timeline dot */}
                <div className={cn(
                  "absolute left-[29px] top-4 w-2.5 h-2.5 rounded-full border-2 border-black z-10 hidden sm:block transition-transform group-hover:scale-125",
                  item.severity === 'CRITICAL' ? 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]' :
                  item.severity === 'WARNING' ? 'bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.5)]' : 'bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.3)]'
                )} />

                <div className="p-5 rounded-2xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] hover:border-white/10 transition-all duration-300">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <span className={cn(
                          "px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-tighter",
                          item.severity === 'WARNING' ? 'bg-amber-500/10 text-amber-400' : 'bg-blue-500/10 text-blue-400'
                        )}>
                          {item.action}
                        </span>
                        <span className="text-xs font-bold text-white/80">{item.actor}</span>
                      </div>
                      <p className="text-sm text-white leading-relaxed font-medium">
                        {item.target}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-[10px] font-bold text-white/20 uppercase tracking-widest">
                        {new Date(item.time || '').toLocaleString()}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
