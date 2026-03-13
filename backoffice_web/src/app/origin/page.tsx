'use client';

import React, { useState, useEffect, useCallback, ReactElement } from 'react';
import { useAuth } from '@/components/AuthProvider';
import api from '@/lib/api';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Table from '@/components/ui/Table';
import Input from '@/components/ui/Input';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';
import SectionHeader from '@/components/ui/SectionHeader';
import StatCard from '@/components/ui/StatCard';
import MoneyCell from '@/components/ui/MoneyCell';
import FilterBar from '@/components/ui/FilterBar';
import LoadingState from '@/components/ui/LoadingState';
import { RefreshCcw, TrendingUp, TrendingDown, Wallet, Send } from 'lucide-react';

interface DailyMovement {
  country: string;
  currency: string;
  total_in: number;
  total_out: number;
  net_balance: number;
}

interface BalanceResponse {
  movements?: DailyMovement[];
  items?: DailyMovement[];
  data?: DailyMovement[];
}

interface SweepRequest {
  country: string;
  currency: string;
  amount: number;
  tx_hash: string;
  notes: string;
}


export default function OriginPage() {
  const { token, isReady } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [movements, setMovements] = useState<DailyMovement[]>([]);
  const [selectedDay, setSelectedDay] = useState('');
  const [sweepDialogOpen, setSweepDialogOpen] = useState(false);
  const [sweepForm, setSweepForm] = useState<SweepRequest>({
    country: '',
    currency: '',
    amount: 0,
    tx_hash: '',
    notes: '',
  });
  const [sweepLoading, setSweepLoading] = useState(false);
  const [sweepSuccess, setSweepSuccess] = useState('');

  useEffect(() => {
    const today = new Date();
    const formatted = today.toISOString().split('T')[0];
    setSelectedDay(formatted);
  }, []);

  const fetchBalance = useCallback(async () => {
    if (!selectedDay || !token) return;
    setLoading(true);
    setError('');
    try {
      const res = await api.get<BalanceResponse | DailyMovement[]>(`/origin_wallets/balance?day=${selectedDay}`);
      const data = res.data;
      const movArray = Array.isArray(data) ? data : (data.movements || data.items || data.data || []);
      setMovements(movArray);
    } catch (err: any) {
      const message = err?.response?.data?.detail || err.message || 'Error desconocido';
      setError(message);
      setMovements([]);
    } finally {
      setLoading(false);
    }
  }, [selectedDay, token]);

  useEffect(() => {
    if (isReady && token && selectedDay) {
      fetchBalance();
    }
  }, [isReady, token, selectedDay, fetchBalance]);

  const openSweepDialog = (country: string, currency: string) => {
    setSweepForm({ country, currency, amount: 0, tx_hash: '', notes: '' });
    setSweepDialogOpen(true);
    setSweepSuccess('');
  };

  const handleSweepSubmit = async () => {
    setSweepLoading(true);
    setError('');
    setSweepSuccess('');
    try {
      await api.post('/origin_wallets/sweeps', sweepForm);
      setSweepSuccess('Sweep registrado exitosamente');
      setSweepDialogOpen(false);
      fetchBalance();
    } catch (err: any) {
      const message = err?.response?.data?.detail || err.message || 'Error desconocido';
      setError(message);
    } finally {
      setSweepLoading(false);
    }
  };

  const safeMovements = Array.isArray(movements) ? movements : [];
  const totalIn = safeMovements.reduce((sum, m) => sum + (m.total_in || 0), 0);
  const totalOut = safeMovements.reduce((sum, m) => sum + (m.total_out || 0), 0);
  const totalNet = safeMovements.reduce((sum, m) => sum + (m.net_balance || 0), 0);

  const columns = [
    { key: 'country', header: 'País', render: (m: DailyMovement) => <span className="font-bold">{m.country}</span> },
    { key: 'currency', header: 'Moneda', render: (m: DailyMovement) => <Badge color="default">{m.currency}</Badge> },
    { 
      key: 'total_in', 
      header: 'Entradas', 
      render: (m: DailyMovement) => (
        <span className="text-emerald-400 font-bold">
          ${(m.total_in || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 })}
        </span>
      )
    },
    { 
      key: 'total_out', 
      header: 'Salidas', 
      render: (m: DailyMovement) => (
        <span className="text-rose-400 font-bold">
          ${(m.total_out || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 })}
        </span>
      )
    },
    { 
      key: 'net_balance', 
      header: 'Balance Neto', 
      render: (m: DailyMovement) => (
        <span className={`font-black ${m.net_balance >= 0 ? 'text-blue-400' : 'text-rose-400'}`}>
          ${(m.net_balance || 0).toLocaleString('es-VE', { minimumFractionDigits: 2 })}
        </span>
      )
    },
    {
      key: 'actions',
      header: 'Gestión de Fondos',
      render: (m: DailyMovement) => (
        <div className="flex justify-center">
          <Button
            size="sm"
            variant="secondary"
            icon={<Send size={14} />}
            onClick={() => openSweepDialog(m.country, m.currency)}
            title="Registrar Sweep"
          >
            Sweep
          </Button>
        </div>
      )
    }
  ];

  if (!isReady || !token) return null;

  return (
    <div className="space-y-8 pb-10">
      {/* Header */}
      <SectionHeader
        title="Billeteras Origen"
        subtitle="Entradas y salidas por país y moneda para el día seleccionado"
        rightSlot={
          <Button
            variant="primary"
            icon={<RefreshCcw size={18} className={loading ? "animate-spin" : ""} />}
            onClick={fetchBalance}
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
            label="Fecha de Consulta"
            value={selectedDay}
            onChange={(e) => setSelectedDay(e.target.value)}
          />
        </div>
        <div className="flex gap-3 pt-2 lg:pt-0">
          <Button variant="secondary" onClick={fetchBalance} loading={loading}>
            Consultar Billeteras
          </Button>
          <Badge color="info">
            Registros: {safeMovements.length}
          </Badge>
        </div>
      </FilterBar>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-500 font-bold animate-shake">
          {error}
        </div>
      )}

      {sweepSuccess && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl text-emerald-500 font-bold flex justify-between items-center">
          {sweepSuccess}
          <button onClick={() => setSweepSuccess('')} className="bg-emerald-500/10 hover:bg-emerald-500/20 p-1 rounded-lg">
            <TrendingDown size={16} />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Total Entradas"
          value={<MoneyCell value={totalIn} emphasize />}
          icon={<TrendingUp size={24} />}
          accentClassName="from-emerald-600/10 to-emerald-500/5 shadow-emerald-900/10"
          subtitle="Acumulado bruto del día en curso"
        />
        <StatCard
          title="Total Salidas (Sweeps)"
          value={<MoneyCell value={totalOut} emphasize />}
          icon={<TrendingDown size={24} />}
          accentClassName="from-rose-600/10 to-rose-500/5 shadow-rose-900/10"
          subtitle="Retiros a Binance u otras carteras"
        />
        <StatCard
          title="Balance de Origen"
          value={<MoneyCell value={totalNet} emphasize />}
          icon={<Wallet size={24} />}
          accentClassName={totalNet >= 0 ? "from-blue-600/10 to-blue-500/5" : "from-rose-600/10 to-rose-500/5"}
          subtitle="Liquidez disponible en origen"
        />
      </div>

      {loading ? (
        <LoadingState title="Consultando liquidez..." />
      ) : (
        <Card className="overflow-hidden">
          <div className="p-6 border-b border-white/5 bg-white/[0.02]">
            <h2 className="text-xl font-black text-white">Detalle de Liquidez en Origen</h2>
            <p className="text-gray-500 text-[10px] font-bold uppercase tracking-widest mt-1">Reporte consolidado por moneda</p>
          </div>
          <Table
            columns={columns}
            data={safeMovements}
            loading={loading}
            emptyMessage="No se detectaron movimientos para la fecha seleccionada"
          />
        </Card>
      )}

      <Modal
        isOpen={sweepDialogOpen}
        onClose={() => setSweepDialogOpen(false)}
        title="Registrar Sweep (Salida a Binance)"
        maxWidth="sm"
        footer={(
          <div className="flex gap-3 justify-end w-full">
            <Button variant="ghost" onClick={() => setSweepDialogOpen(false)}>Cancelar</Button>
            <Button
              variant="primary"
              onClick={handleSweepSubmit}
              loading={sweepLoading}
              disabled={!sweepForm.amount || !sweepForm.tx_hash}
            >
              Confirmar Envío
            </Button>
          </div>
        )}
      >
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <Input label="País" value={sweepForm.country} disabled />
            <Input label="Moneda" value={sweepForm.currency} disabled />
          </div>
          <Input
            label="Monto de Salida"
            type="number"
            value={sweepForm.amount}
            onChange={(e) => setSweepForm({ ...sweepForm, amount: parseFloat(e.target.value) || 0 })}
            required
            helperText="El monto será restado del balance disponible en origen"
          />
          <Input
            label="TX Hash / Referencia"
            value={sweepForm.tx_hash}
            onChange={(e) => setSweepForm({ ...sweepForm, tx_hash: e.target.value })}
            required
            placeholder="Hash de la transacción en Binance/Blockchain"
          />
          <Input
            label="Notas Adicionales"
            value={sweepForm.notes}
            onChange={(e) => setSweepForm({ ...sweepForm, notes: e.target.value })}
            multiline
            rows={3}
            placeholder="Detalles sobre el envío..."
          />
        </div>
      </Modal>
    </div>
  );
}