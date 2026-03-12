'use client';

import React, { useState, useEffect, useCallback, ReactElement } from 'react';
import {
  Tooltip,
  IconButton,
  MenuItem,
  Select,
  FormControl,
} from '@mui/material';
import {
  TrendingUp as InIcon,
  TrendingDown as OutIcon,
  AccountBalance as BalanceIcon,
  Send as SendIcon,
  Refresh as RefreshIcon,
  InfoOutlined as InfoIcon,
} from '@mui/icons-material';
import { useAuth } from '@/components/AuthProvider';
import api from '@/lib/api';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Table from '@/components/ui/Table';
import Input from '@/components/ui/Input';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';

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

interface StatCardProps {
  title: string;
  value: string;
  icon: ReactElement;
  color: string;
  bg?: string;
  hint?: string;
}

function StatCard({ title, value, icon, color, bg, hint }: StatCardProps) {
  return (
    <Card className="flex-1 min-w-[260px] p-6 hover:-translate-y-1">
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">{title}</span>
            {hint && (
              <Tooltip title={hint}>
                <span className="cursor-help"><InfoIcon sx={{ fontSize: 14, color: 'rgba(255,255,255,0.2)' }} /></span>
              </Tooltip>
            )}
          </div>
          <h3 className="text-3xl font-black text-white mt-2 tracking-tight">{value}</h3>
        </div>
        <div className="p-3 rounded-2xl bg-white/5 border border-white/10">
          {React.cloneElement(icon, { sx: { color, fontSize: 24 } })}
        </div>
      </div>
    </Card>
  );
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
            icon={<SendIcon sx={{ fontSize: 14 }} />}
            onClick={() => openSweepDialog(m.country, m.currency)}
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
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-black text-white tracking-tight">
            Billeteras Origen
          </h1>
          <p className="text-gray-500 font-medium mt-1">
            Entradas y salidas por país y moneda para el día seleccionado
          </p>
        </div>
        <Button
          variant="primary"
          icon={<RefreshIcon sx={{ fontSize: 18 }} />}
          onClick={fetchBalance}
          loading={loading}
        >
          Actualizar
        </Button>
      </div>

      <Card className="p-4 bg-primary-800/20">
        <div className="flex flex-col md:flex-row items-end gap-6">
          <Input
            type="date"
            label="Fecha de Consulta"
            value={selectedDay}
            onChange={(e) => setSelectedDay(e.target.value)}
            className="w-full md:w-60"
          />
          <Button variant="secondary" onClick={fetchBalance} loading={loading}>
            Consultar Billeteras
          </Button>
          <div className="flex-1" />
          <Badge color="info" className="px-4 py-1.5">
            Registros: {safeMovements.length}
          </Badge>
        </div>
      </Card>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl text-rose-500 font-bold animate-shake">
          {error}
        </div>
      )}

      {sweepSuccess && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl text-emerald-500 font-bold flex justify-between items-center">
          {sweepSuccess}
          <button onClick={() => setSweepSuccess('')} className="bg-emerald-500/10 hover:bg-emerald-500/20 p-1 rounded-lg">
            <OutIcon size={16} />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Total Entradas"
          value={`$${totalIn.toLocaleString('es-VE', { minimumFractionDigits: 2 })}`}
          icon={<InIcon sx={{ fontSize: 24 }} />}
          color="#10b981"
          hint="Suma total de entradas del día en USD aproximado"
        />
        <StatCard
          title="Total Salidas (Sweeps)"
          value={`$${totalOut.toLocaleString('es-VE', { minimumFractionDigits: 2 })}`}
          icon={<OutIcon sx={{ fontSize: 24 }} />}
          color="#f43f5e"
          hint="Suma total de salidas/sweeps del día hacia Binance u otras carteras"
        />
        <StatCard
          title="Balance de Origen"
          value={`$${totalNet.toLocaleString('es-VE', { minimumFractionDigits: 2 })}`}
          icon={<BalanceIcon sx={{ fontSize: 24 }} />}
          color={totalNet >= 0 ? '#3b82f6' : '#f43f5e'}
          hint="Fondos disponibles en origen (Entradas - Salidas)"
        />
      </div>

      <Card className="overflow-hidden">
        <div className="p-6 border-b border-white/5 bg-white/5">
          <h2 className="text-xl font-black text-white">Detalle de Liquidez en Origen</h2>
          <p className="text-gray-500 text-xs font-bold uppercase tracking-widest mt-1">Reporte consolidado por moneda</p>
        </div>
        <Table
          columns={columns}
          data={safeMovements}
          loading={loading}
          emptyMessage="No se detectaron movimientos para la fecha seleccionada"
        />
      </Card>

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