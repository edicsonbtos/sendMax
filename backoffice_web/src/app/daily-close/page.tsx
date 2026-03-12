'use client';
import { useState, useEffect } from 'react';
import { apiGet, apiPost } from '@/lib/api';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Table from '@/components/ui/Table';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';
import Input from '@/components/ui/Input';
import {
    Lock, Download, Calendar, TrendingUp, AlertTriangle,
    CheckCircle, FileText, DollarSign
} from 'lucide-react';
import { format, subDays } from 'date-fns';
import { es } from 'date-fns/locale';
import toast from 'react-hot-toast';

interface DailyClosure {
    id: number;
    closure_date: string;
    created_at: string;
    total_orders_count: number;
    total_volume_origin: number;
    total_profit_real: number;
    success_rate: number;
    best_operator_alias: string | null;
    best_origin_country: string | null;
    best_dest_country: string | null;
    pending_withdrawals_count: number;
    pending_withdrawals_amount: number;
    notes: string | null;
}

export default function DailyClosePage() {
    const [closures, setClosures] = useState<DailyClosure[]>([]);
    const [loading, setLoading] = useState(true);
    const [executeModalOpen, setExecuteModalOpen] = useState(false);
    const [selectedDate, setSelectedDate] = useState('');
    const [notes, setNotes] = useState('');
    const [executing, setExecuting] = useState(false);

    useEffect(() => {
        loadClosures();
        const yesterday = format(subDays(new Date(), 1), 'yyyy-MM-dd');
        setSelectedDate(yesterday);
    }, []);

    const loadClosures = async () => {
        setLoading(true);
        try {
            const response = await apiGet<DailyClosure[]>('/api/admin/daily-close/history?limit=30');
            setClosures(response.data);
        } catch (error) {
            console.error('Error loading closures:', error);
            toast.error('Error al cargar cierres');
        } finally {
            setLoading(false);
        }
    };

    const handleExecuteClose = async () => {
        if (!selectedDate) {
            toast.error('Selecciona una fecha');
            return;
        }

        setExecuting(true);
        try {
            await apiPost('/api/admin/daily-close/execute', {
                closure_date: selectedDate,
                notes: notes || null,
                force: false
            });

            toast.success(`Cierre del ${selectedDate} ejecutado correctamente`);
            setExecuteModalOpen(false);
            setNotes('');
            loadClosures();
        } catch (error: any) {
            const detail = error.response?.data?.detail || 'Error al ejecutar cierre';
            toast.error(detail);
        } finally {
            setExecuting(false);
        }
    };

    const handleExportCSV = async (date: string) => {
        try {
            const response = await apiPost(
                `/api/admin/daily-close/${date}/export-csv`,
                {},
                { responseType: 'blob' }
            );

            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `cierre_${date}.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();

            toast.success('CSV descargado');
        } catch (error) {
            toast.error('Error al exportar');
        }
    };

    const columns = [
        {
            key: 'closure_date',
            header: 'Fecha',
            render: (row: DailyClosure) => (
                <span className="font-medium">
                    {format(new Date(row.closure_date), 'dd MMM yyyy', { locale: es })}
                </span>
            ),
        },
        {
            key: 'total_orders_count',
            header: 'Órdenes',
            render: (row: DailyClosure) => (
                <div className="font-semibold text-cyan-400">{row.total_orders_count}</div>
            ),
        },
        {
            key: 'total_volume_origin',
            header: 'Volumen',
            render: (row: DailyClosure) => (
                <span className="text-blue-400">
                    ${Number(row.total_volume_origin).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </span>
            ),
        },
        {
            key: 'total_profit_real',
            header: 'Ganancia Real',
            render: (row: DailyClosure) => (
                <span className="text-green-400 font-semibold">
                    ${Number(row.total_profit_real).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </span>
            ),
        },
        {
            key: 'success_rate',
            header: 'Tasa Éxito',
            render: (row: DailyClosure) => (
                <Badge color={
                    row.success_rate >= 80 ? 'success' :
                        row.success_rate >= 50 ? 'warning' : 'danger'
                }>
                    {Number(row.success_rate).toFixed(1)}%
                </Badge>
            ),
        },
        {
            key: 'best_operator_alias',
            header: 'Top Operador',
            render: (row: DailyClosure) => (
                <span className="text-purple-400">{row.best_operator_alias || '-'}</span>
            ),
        },
        {
            key: 'best_origin_country',
            header: 'País Origen',
            render: (row: DailyClosure) => row.best_origin_country || '-',
        },
        {
            key: 'actions',
            header: 'Acciones',
            render: (row: DailyClosure) => (
                <Button
                    size="sm"
                    variant="ghost"
                    icon={<Download size={14} />}
                    onClick={() => handleExportCSV(row.closure_date)}
                >
                    CSV
                </Button>
            ),
        },
    ];

    const stats = {
        totalClosures: closures.length,
        totalProfit: closures.reduce((acc, c) => acc + Number(c.total_profit_real), 0),
        avgSuccessRate: closures.length > 0
            ? closures.reduce((acc, c) => acc + Number(c.success_rate), 0) / closures.length
            : 0,
        totalOrders: closures.reduce((acc, c) => acc + c.total_orders_count, 0),
    };

    return (
        <div className="space-y-6 animate-slide-up">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold mb-2">Cierre Diario</h1>
                    <p className="text-gray-400">Gestión de cierres contables y reportería</p>
                </div>
                <Button
                    variant="primary"
                    icon={<Lock size={18} />}
                    onClick={() => setExecuteModalOpen(true)}
                >
                    Ejecutar Cierre
                </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <Card hover className="p-6">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-cyan-500/20 rounded-xl flex items-center justify-center">
                            <Calendar size={24} className="text-cyan-400" />
                        </div>
                        <div>
                            <p className="text-gray-400 text-sm">Días Cerrados</p>
                            <p className="text-2xl font-bold">{stats.totalClosures}</p>
                        </div>
                    </div>
                </Card>

                <Card hover className="p-6">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center">
                            <DollarSign size={24} className="text-green-400" />
                        </div>
                        <div>
                            <p className="text-gray-400 text-sm">Ganancia Total</p>
                            <p className="text-2xl font-bold text-green-400">
                                ${stats.totalProfit.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                            </p>
                        </div>
                    </div>
                </Card>

                <Card hover className="p-6">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-blue-500/20 rounded-xl flex items-center justify-center">
                            <TrendingUp size={24} className="text-blue-400" />
                        </div>
                        <div>
                            <p className="text-gray-400 text-sm">Tasa Éxito Promedio</p>
                            <p className="text-2xl font-bold">{stats.avgSuccessRate.toFixed(1)}%</p>
                        </div>
                    </div>
                </Card>

                <Card hover className="p-6">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center">
                            <FileText size={24} className="text-purple-400" />
                        </div>
                        <div>
                            <p className="text-gray-400 text-sm">Órdenes Totales</p>
                            <p className="text-2xl font-bold">{stats.totalOrders}</p>
                        </div>
                    </div>
                </Card>
            </div>

            <Card className="p-6">
                <div className="mb-4">
                    <h3 className="text-xl font-semibold">Historial de Cierres</h3>
                </div>
                <Table
                    data={closures}
                    columns={columns}
                    loading={loading}
                    emptyMessage="No hay cierres registrados"
                />
            </Card>

            <Modal
                isOpen={executeModalOpen}
                onClose={() => setExecuteModalOpen(false)}
                title="Ejecutar Cierre Diario"
                footer={
                    <>
                        <Button variant="ghost" onClick={() => setExecuteModalOpen(false)}>
                            Cancelar
                        </Button>
                        <Button
                            variant="primary"
                            loading={executing}
                            onClick={handleExecuteClose}
                            icon={<Lock size={18} />}
                        >
                            Ejecutar Cierre
                        </Button>
                    </>
                }
            >
                <div className="space-y-4">
                    <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                        <h4 className="font-semibold mb-2 flex items-center gap-2">
                            <AlertTriangle size={16} className="text-blue-400" />
                            Importante
                        </h4>
                        <ul className="text-sm text-gray-400 space-y-1 list-disc list-inside">
                            <li>El cierre captura un snapshot inmutable de todas las métricas</li>
                            <li>Una vez cerrado, no se pueden modificar órdenes de ese día</li>
                            <li>Verifica que todas las operaciones estén completas</li>
                        </ul>
                    </div>

                    <Input
                        type="date"
                        label="Fecha del Cierre"
                        value={selectedDate}
                        onChange={(e) => setSelectedDate(e.target.value)}
                        max={format(subDays(new Date(), 1), 'yyyy-MM-dd')}
                    />

                    <Input
                        label="Notas (opcional)"
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Ej: Ajuste manual por orden #1234"
                    />

                    <div className="pt-4 border-t border-gray-800">
                        <h4 className="font-semibold mb-3">Métricas que se capturarán:</h4>
                        <div className="grid grid-cols-2 gap-3 text-sm">
                            {[
                                'Órdenes completadas',
                                'Volumen total',
                                'Ganancia real',
                                'Mejor operador',
                                'Mejor país',
                                'Retiros pendientes',
                                'Estado de billeteras',
                                'Snapshots de vaults'
                            ].map((metric, i) => (
                                <div key={i} className="flex items-center gap-2">
                                    <CheckCircle size={16} className="text-green-400" />
                                    <span className="text-gray-300">{metric}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </Modal>
        </div>
    );
}