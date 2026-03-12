'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Refresh as RefreshIcon,
  TrendingUp as InIcon,
  TrendingDown as OutIcon,
  AccountBalance as BalanceIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Download as DownloadIcon,
  Lock as LockIcon,
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import api from '@/lib/api';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Table from '@/components/ui/Table';
import Input from '@/components/ui/Input';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';

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
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-black text-white tracking-tight">
            Cierre Diario
          </h1>
          <p className="text-gray-500 font-medium mt-1">
            Reporte de cierre y consolidación operativa por día
          </p>
        </div>
        <Button
          variant="primary"
          icon={<RefreshIcon sx={{ fontSize: 18 }} />}
          onClick={fetchReport}
          loading={loading}
        >
          Actualizar
        </Button>
      </div>

      <Card className="p-4 bg-primary-800/20">
        <div className="flex flex-col md:flex-row items-end gap-6">
          <Input
            type="date"
            label="Día de Operación"
            value={selectedDay}
            onChange={(e) => setSelectedDay(e.target.value)}
            className="w-full md:w-60"
          />
          <div className="flex gap-3">
            <Button variant="secondary" onClick={fetchReport} loading={loading}>
              Consultar Reporte
            </Button>
            <Button
              variant="secondary"
              icon={<DownloadIcon sx={{ fontSize: 18 }} />}
              onClick={exportCSV}
              disabled={safeReport.length === 0}
            >
              Exportar
            </Button>
          </div>
          <div className="flex-1" />
          <Badge color="info" className="px-4 py-1.5">
            Periodo: {selectedDay}
          </Badge>
        </div>
      </Card>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-500 font-bold animate-shake">
          {error}
        </div>
      )}

      {closeResult && (
        <div className={`p-4 rounded-2xl border flex flex-col gap-1 ${
          closeResult.status === 'already_closed' 
            ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' 
            : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
        }`}>
          <div className="flex items-center gap-2 font-bold">
            <CheckIcon size={20} />
            {closeResult.message}
          </div>
          {closeResult.closed_at && (
            <span className="text-xs opacity-70 ml-7">
              Sincronizado el: {new Date(closeResult.closed_at).toLocaleString('es-VE')}
            </span>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <KPIDisplay
          title="Total Entradas"
          value={`$${totalIn.toLocaleString('es-VE', { minimumFractionDigits: 2 })}`}
          icon={<InIcon sx={{ fontSize: 24 }} />}
          color="#10b981"
        />
        <KPIDisplay
          title="Total Salidas"
          value={`$${totalOut.toLocaleString('es-VE', { minimumFractionDigits: 2 })}`}
          icon={<OutIcon sx={{ fontSize: 24 }} />}
          color="#f43f5e"
        />
        <KPIDisplay
          title="Balance Neto"
          value={`$${totalNet.toLocaleString('es-VE', { minimumFractionDigits: 2 })}`}
          icon={<BalanceIcon sx={{ fontSize: 24 }} />}
          color={totalNet >= 0 ? '#3b82f6' : '#f43f5e'}
        />
      </div>

      <Card className="overflow-hidden">
        <div className="p-6 border-b border-white/5 bg-white/5">
          <h2 className="text-xl font-black text-white">Detalle por País / Moneda</h2>
          <p className="text-gray-500 text-xs font-bold uppercase tracking-widest mt-1">Corte de caja para el día {selectedDay}</p>
        </div>
        <Table
          columns={columns}
          data={safeReport}
          loading={loading}
          emptyMessage="No hay registros para la fecha seleccionada"
        />
      </Card>

      <Card className="p-8 border-amber-500/30 bg-amber-500/5 flex flex-col md:flex-row justify-between items-center gap-6">
        <div className="flex items-center gap-4">
          <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-500">
            <WarningIcon size={32} />
          </div>
          <div>
            <h3 className="text-xl font-black text-amber-500">Acción de Cierre</h3>
            <p className="text-amber-500/70 font-medium">Bloquea las operaciones del día y genera el reporte histórico final.</p>
          </div>
        </div>
        <Button
          variant="primary"
          size="lg"
          icon={<LockIcon size={20} />}
          onClick={() => setCloseDialogOpen(true)}
          disabled={safeReport.length === 0}
          className="bg-amber-600 hover:bg-amber-700 border-amber-500 shadow-amber-900/40 w-full md:w-auto"
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
              icon={<LockIcon size={18} />}
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