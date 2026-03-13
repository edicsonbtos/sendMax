'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/components/AuthProvider';
import api from '@/lib/api';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Table from '@/components/ui/Table';
import Input from '@/components/ui/Input';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';
import SectionHeader from '@/components/ui/SectionHeader';
import MetricCard from '@/components/ui/MetricCard';
import FilterBar from '@/components/ui/FilterBar';
import LoadingState from '@/components/ui/LoadingState';
import MoneyCell from '@/components/ui/MoneyCell';
import { RefreshCcw, TrendingUp, TrendingDown, ClipboardCheck, Lock, Download, CheckCircle2 } from 'lucide-react';

interface CloseReportItem {
  country: string;
  currency: string;
  total_in: number;
  total_out: number;
  net_balance: number;
}

interface CloseReportResponse {
  report?: CloseReportItem[];
  items?: CloseReportItem[];
  data?: CloseReportItem[];
}

interface CloseResponse {
  status: string;
  day: string;
  message: string;
  closed_at?: string;
}

export default function DailyClosePage() {
  const { token, isReady } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedDay, setSelectedDay] = useState('');
  const [report, setReport] = useState<CloseReportItem[]>([]);
  const [closeDialogOpen, setCloseDialogOpen] = useState(false);
  const [closeLoading, setCloseLoading] = useState(false);
  const [closeResult, setCloseResult] = useState<CloseResponse | null>(null);

  useEffect(() => {
    const today = new Date();
    today.setDate(today.getDate() - 1);
    const formatted = today.toISOString().split('T')[0];
    setSelectedDay(formatted);
  }, []);

  const fetchReport = useCallback(async () => {
    if (!selectedDay || !token) return;
    setLoading(true);
    setError('');
    setCloseResult(null);
    try {
      const res = await api.get<CloseReportResponse | CloseReportItem[]>(`/daily_closure/report?day=${selectedDay}`);
      const data = res.data;
      const reportArray = Array.isArray(data) ? data : (data.report || data.items || data.data || []);
      setReport(reportArray);
    } catch (err: any) {
      const message = err?.response?.data?.detail || err.message || 'Error desconocido';
      setError(message);
      setReport([]);
    } finally {
      setLoading(false);
    }
  }, [selectedDay, token]);

  useEffect(() => {
    if (isReady && token && selectedDay) {
      fetchReport();
    }
  }, [isReady, token, selectedDay, fetchReport]);

  const handleCloseDay = async () => {
    setCloseLoading(true);
    setError('');
    try {
      const res = await api.post<CloseResponse>('/daily_closure/close', { day: selectedDay });
      setCloseResult(res.data);
      setCloseDialogOpen(false);
      fetchReport();
    } catch (err: any) {
      const message = err?.response?.data?.detail || err.message || 'Error desconocido';
      setError(message);
    } finally {
      setCloseLoading(false);
    }
  };

  const exportCSV = () => {
    if (!Array.isArray(report) || report.length === 0) return;
    const headers = ['Pais', 'Moneda', 'Entradas', 'Salidas', 'Balance Neto'];
    const rows = report.map(r => [
      r.country,
      r.currency,
      (r.total_in || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 }),
      (r.total_out || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 }),
      (r.net_balance || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 }),
    ]);
    const csvContent = [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `cierre_${selectedDay}.csv`;
    link.click();
  };

  const safeReport = Array.isArray(report) ? report : [];
  const totalIn = safeReport.reduce((sum, r) => sum + (r.total_in || 0), 0);
  const totalOut = safeReport.reduce((sum, r) => sum + (r.total_out || 0), 0);
  const totalNet = safeReport.reduce((sum, r) => sum + (r.net_balance || 0), 0);

  const columns = [
    { key: 'country', header: 'País', render: (item: CloseReportItem) => <span className="font-bold">{item.country}</span> },
    { key: 'currency', header: 'Moneda', render: (item: CloseReportItem) => <Badge color="default">{item.currency}</Badge> },
    { 
      key: 'total_in', 
      header: 'Entradas', 
      render: (item: CloseReportItem) => (
        <span className="text-emerald-400 font-bold">
          ${(item.total_in || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 })}
        </span>
      )
    },
    { 
      key: 'total_out', 
      header: 'Salidas', 
      render: (item: CloseReportItem) => (
        <span className="text-rose-400 font-bold">
          ${(item.total_out || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 })}
        </span>
      )
    },
    { 
      key: 'net_balance', 
      header: 'Balance Neto', 
      render: (item: CloseReportItem) => (
        <span className={`font-black ${item.net_balance >= 0 ? 'text-blue-400' : 'text-rose-400'}`}>
          ${(item.net_balance || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 })}
        </span>
      )
    }
  ];

  if (!isReady || !token) return null;

  return (
    <div className="space-y-8 pb-10">
      {/* Header */}
      <SectionHeader
        title="Cierre Diario"
        subtitle="Reporte de cierre y consolidación operativa por día"
        rightSlot={
          <Button
            variant="primary"
            icon={<RefreshCcw size={18} className={loading ? "animate-spin" : ""} />}
            onClick={fetchReport}
            loading={loading}
          >
            Actualizar
          </Button>
        }
      />

      <FilterBar>
        <div className="w-full md:w-64">
          <Input
            type="date"
            label="Día de Operación"
            value={selectedDay}
            onChange={(e) => setSelectedDay(e.target.value)}
          />
        </div>
        <div className="flex gap-3 pt-2 lg:pt-0">
          <Button variant="secondary" onClick={fetchReport} loading={loading}>
            Consultar Reporte
          </Button>
          <Button
            variant="secondary"
            icon={<Download size={18} />}
            onClick={exportCSV}
            disabled={safeReport.length === 0}
          >
            Exportar CSV
          </Button>
          <Badge color="info">
            Periodo: {selectedDay}
          </Badge>
        </div>
      </FilterBar>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-500 font-bold animate-shake">
          {error}
        </div>
      )}

      {closeResult && (
        <div className={`p-5 rounded-2xl border flex flex-col gap-1 ${
          closeResult.status === 'already_closed' 
            ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' 
            : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
        }`}>
          <div className="flex items-center gap-3 font-black tracking-tight">
            <CheckCircle2 size={24} />
            {closeResult.message}
          </div>
          {closeResult.closed_at && (
            <span className="text-[10px] uppercase font-bold tracking-widest opacity-40 ml-9">
              Sincronizado el: {new Date(closeResult.closed_at).toLocaleString('es-VE')}
            </span>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard
          label="Total Entradas"
          value={<MoneyCell value={totalIn} emphasize />}
          icon={<TrendingUp size={24} />}
          trendDirection="up"
          hint="Volumen bruto recibido"
        />
        <MetricCard
          label="Total Salidas"
          value={<MoneyCell value={totalOut} emphasize />}
          icon={<TrendingDown size={24} />}
          trendDirection="down"
          hint="Egresos y transferencias"
        />
        <MetricCard
          label="Balance Neto"
          value={<MoneyCell value={totalNet} emphasize />}
          icon={<ClipboardCheck size={24} />}
          trendDirection={totalNet >= 0 ? "neutral" : "down"}
          hint="Resultado operativo del día"
        />
      </div>

      {loading ? (
        <LoadingState title="Generando reporte..." />
      ) : (
        <Card className="overflow-hidden">
          <div className="p-6 border-b border-white/5 bg-white/[0.02]">
            <h2 className="text-xl font-black text-white">Detalle por País / Moneda</h2>
            <p className="text-gray-500 text-[10px] font-bold uppercase tracking-widest mt-1">Corte de caja para el día {selectedDay}</p>
          </div>
          <Table
            columns={columns}
            data={safeReport}
            loading={loading}
            emptyMessage="No hay registros para la fecha seleccionada"
          />
        </Card>
      )}

      <Card className="p-8 border-amber-500/20 bg-amber-500/[0.03] backdrop-blur-md flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="flex items-center gap-4">
          <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-500">
            <Lock size={32} />
          </div>
          <div>
            <h3 className="text-xl font-black text-amber-500 tracking-tight">Acción de Cierre</h3>
            <p className="text-amber-500/50 font-medium text-sm">Bloquea las operaciones del día y genera el reporte histórico final.</p>
          </div>
        </div>
        <Button
          variant="primary"
          size="lg"
          icon={<Lock size={20} />}
          onClick={() => setCloseDialogOpen(true)}
          disabled={safeReport.length === 0}
          className="bg-amber-600 hover:bg-amber-700 border-amber-500 shadow-amber-900/40 w-full md:w-auto text-white"
        >
          Cerrar Día {selectedDay}
        </Button>
      </Card>

      <Modal
        isOpen={closeDialogOpen}
        onClose={() => setCloseDialogOpen(false)}
        title="Confirmar Cierre Maestro"
        footer={(
          <div className="flex gap-3 justify-end w-full">
            <Button variant="ghost" onClick={() => setCloseDialogOpen(false)}>Cancelar</Button>
            <Button
              variant="primary"
              icon={<Lock size={18} />}
              onClick={handleCloseDay}
              loading={closeLoading}
            >
              Confirmar Cierre
            </Button>
          </div>
        )}
      >
        <div className="space-y-4">
          <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl text-amber-500 font-bold text-center">
            Atención: Estás cerrando el día {selectedDay}
          </div>
          <p className="text-gray-400 leading-relaxed text-center">
            Este proceso consolidará todas las entradas y salidas registradas. 
            El reporte resultante servirá como base para la tesorería central.
          </p>
        </div>
      </Modal>
    </div>
  );
}

function KPIDisplay({ title, value, icon, color }: { title: string, value: string, icon: any, color: string }) {
  return (
    <Card className="flex-1 min-w-[260px] p-6">
      <div className="flex justify-between items-start">
        <div>
          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">{title}</span>
          <h3 className="text-3xl font-black text-white mt-2 tracking-tight">{value}</h3>
        </div>
        <div className="p-3 rounded-2xl bg-white/5 border border-white/10">
          {React.cloneElement(icon, { sx: { color, fontSize: 24 } })}
        </div>
      </div>
    </Card>
  );
}