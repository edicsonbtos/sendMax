'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api'; // FIXED: Importar cliente API para autorizar peticiones
import { safeToFixed } from '@/lib/utils';
import {
    TrendingUp,
    Users,
    Wallet,
    ArrowUpRight,
    Clock,
    Trophy,
    Target,
    Zap
} from 'lucide-react';

// Interfaces
interface Rate {
    origin: string;
    dest: string;
    rate: number;
    commission_pct: number;
}

interface TopClient {
    name: string;
    phone: string;
    total_volume_usdt: number;
    total_orders: number;
}

interface OrderQueue {
    public_id: number;
    client_name: string;
    amount_origin: number;
    origin_country: string;
    dest_country: string;
    status: string;
    created_at: string;
}

interface Stats {
    daily_volume_usdt: number;
    monthly_volume_usdt: number;
    total_orders: number;
    pending_orders: number;
    trust_score: number;
    rank_position: number;
}

interface RankingEntry {
    position: number;
    alias: string;
    trust_score: number;
    total_orders: number;
    monthly_volume_usdt: number;
    is_current_user: boolean;
}

// Banderas de países
const countryFlags: Record<string, string> = {
    'VENEZUELA': '🇻🇪',
    'COLOMBIA': '🇨🇴',
    'ARGENTINA': '🇦🇷',
    'CHILE': '🇨🇱',
    'PERU': '🇵🇪',
    'MEXICO': '🇲🇽',
    'ECUADOR': '🇪🇨',
    'PANAMA': '🇵🇦',
    'USA': '🇺🇸',
    'SPAIN': '🇪🇸',
};

export default function Dashboard() {
    const [rates, setRates] = useState<Rate[]>([]);
    const [topClients, setTopClients] = useState<TopClient[]>([]);
    const [orderQueue, setOrderQueue] = useState<OrderQueue[]>([]);
    const [stats, setStats] = useState<Stats | null>(null);
    const [ranking, setRanking] = useState<RankingEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        let mounted = true;

        const loadInitialData = async () => {
            if (mounted) {
                await fetchAllData();
            }
        };

        loadInitialData();

        const interval = setInterval(() => {
            if (mounted) {
                fetchRates();
            }
        }, 30000);

        return () => {
            mounted = false;
            clearInterval(interval);
        };
    }, []);

    const fetchAllData = async () => {
        setLoading(true);
        await Promise.all([
            fetchRates(),
            fetchTopClients(),
            fetchOrderQueue(),
            fetchStats(),
            fetchRanking()
        ]);
        setLoading(false);
    };

    const fetchRates = async () => {
        try {
            const res = await api.get('/api/rates/current'); // FIXED: Usar api.get
            setRates(res.data.rates?.slice(0, 8) || []);
        } catch (err) {
            console.error('Error fetching rates:', err);
        }
    };

    const fetchTopClients = async () => {
        try {
            const res = await api.get('/api/operators/dashboard/top-clients?limit=5'); // FIXED: Usar api.get
            setTopClients(res.data || []);
        } catch (err) {
            console.error('Error fetching top clients:', err);
        }
    };

    const fetchOrderQueue = async () => {
        try {
            const res = await api.get('/api/operators/orders/queue'); // FIXED: Usar api.get
            setOrderQueue(res.data?.slice(0, 5) || []);
        } catch (err) {
            console.error('Error fetching orders:', err);
        }
    };

    const fetchStats = async () => {
        try {
            const res = await api.get('/api/operators/dashboard/stats'); // FIXED: Usar api.get
            console.log("Datos del backend:", res.data); // <-- AGREGADO POR ANTIGRAVITI
            setStats(res.data);
        } catch (err) {
            console.error('Error fetching stats:', err);
        }
    };

    const fetchRanking = async () => {
        try {
            const res = await api.get('/api/ranking/operators?limit=10'); // FIXED: Usar api.get
            setRanking(res.data || []);
        } catch (err) {
            console.error('Error fetching ranking:', err);
        }
    };

    const formatCurrency = (value: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
        }).format(value);
    };

    const getStatusColor = (status: string) => {
        switch (status.toUpperCase()) {
            case 'COMPLETADA': return 'badge-success';
            case 'PENDIENTE':
            case 'CREADA': return 'badge-warning';
            case 'CANCELADA': return 'badge-error';
            default: return 'badge-info';
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-gray-300">Cargando dashboard...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6 animate-slide-up">
            {/* Header con Stats */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Panel de Operador</h1>
                    <p className="text-gray-400">Bienvenido de vuelta. Aquí está tu resumen.</p>
                </div>
                <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 px-4 py-2 bg-green-500/20 rounded-full border border-green-500/30">
                        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                        <span className="text-green-400 text-sm font-medium">Conectado</span>
                    </div>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="card-glass p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-3 bg-blue-500/20 rounded-xl">
                            <Wallet className="w-6 h-6 text-blue-400" />
                        </div>
                        <span className="badge badge-success">
                            <ArrowUpRight className="w-3 h-3 inline mr-1" />
                            +12%
                        </span>
                    </div>
                    <h3 className="text-gray-400 text-sm font-medium mb-1">Volumen Diario</h3>
                    <p className="text-2xl font-bold text-white">{formatCurrency(stats?.daily_volume_usdt || 0)}</p>
                </div>

                <div className="card-glass p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-3 bg-green-500/20 rounded-xl">
                            <TrendingUp className="w-6 h-6 text-green-400" />
                        </div>
                        <span className="badge badge-success">
                            <ArrowUpRight className="w-3 h-3 inline mr-1" />
                            +8%
                        </span>
                    </div>
                    <h3 className="text-gray-400 text-sm font-medium mb-1">Volumen Mensual</h3>
                    <p className="text-2xl font-bold text-white">{formatCurrency(stats?.monthly_volume_usdt || 0)}</p>
                </div>

                <div className="card-glass p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-3 bg-purple-500/20 rounded-xl">
                            <Users className="w-6 h-6 text-purple-400" />
                        </div>
                    </div>
                    <h3 className="text-gray-400 text-sm font-medium mb-1">Total Órdenes</h3>
                    <p className="text-2xl font-bold text-white">{stats?.total_orders || 0}</p>
                    <p className="text-sm text-yellow-400 mt-2">
                        <Clock className="w-3 h-3 inline mr-1" />
                        {stats?.pending_orders || 0} pendientes
                    </p>
                </div>

                <div className="card-glass p-6">
                    <div className="flex items-center justify-between mb-4">
                        <div className="p-3 bg-yellow-500/20 rounded-xl">
                            <Trophy className="w-6 h-6 text-yellow-400" />
                        </div>
                        <span className="badge badge-warning">#{stats?.rank_position || '-'}</span>
                    </div>
                    <h3 className="text-gray-400 text-sm font-medium mb-1">Trust Score</h3>
                    <p className="text-2xl font-bold text-white">{safeToFixed(stats?.trust_score, 1)}%</p>
                </div>
            </div>

            {/* Main Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                {/* Tasas en Tiempo Real - Columna Grande */}
                <div className="lg:col-span-2 card-glass p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-xl font-bold text-white flex items-center gap-2">
                            <Zap className="w-5 h-5 text-blue-400" />
                            Tasas en Tiempo Real
                        </h2>
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                            Actualizando cada 30s
                        </div>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {rates.map((rate, index) => (
                            <div
                                key={index}
                                className="p-4 bg-white/5 rounded-xl border border-white/10 hover:border-blue-500/50 transition-all"
                            >
                                <div className="flex items-center gap-2 mb-2">
                                    <span className="text-xl">{countryFlags[rate.origin] || '🌍'}</span>
                                    <span className="text-gray-400">→</span>
                                    <span className="text-xl">{countryFlags[rate.dest] || '🌍'}</span>
                                </div>
                                <p className="text-xs text-gray-400 mb-1">{rate.origin} → {rate.dest}</p>
                                <p className="text-lg font-bold text-white">{safeToFixed(rate.rate, 4)}</p>
                                <p className="text-xs text-green-400">+{safeToFixed(rate.commission_pct, 1)}% comisión</p>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Ranking de Operadores */}
                <div className="card-glass p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-xl font-bold text-white flex items-center gap-2">
                            <Trophy className="w-5 h-5 text-yellow-400" />
                            Top Operadores
                        </h2>
                    </div>
                    <div className="space-y-3">
                        {ranking.slice(0, 5).map((entry, index) => (
                            <div
                                key={index}
                                className={`flex items-center gap-4 p-3 rounded-xl transition-all ${entry.is_current_user
                                    ? 'bg-blue-500/20 border border-blue-500/50'
                                    : 'bg-white/5 hover:bg-white/10'
                                    }`}
                            >
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${index === 0 ? 'bg-yellow-500 text-black' :
                                    index === 1 ? 'bg-gray-400 text-black' :
                                        index === 2 ? 'bg-orange-600 text-white' :
                                            'bg-white/10 text-white'
                                    }`}>
                                    {entry.position}
                                </div>
                                <div className="flex-1">
                                    <p className="font-medium text-white">{entry.alias || 'Operador'}</p>
                                    <p className="text-xs text-gray-400">{entry.total_orders} órdenes</p>
                                </div>
                                <div className="text-right">
                                    <p className="text-sm font-bold text-white">{safeToFixed(entry.trust_score, 0)}%</p>
                                    <p className="text-xs text-green-400">{formatCurrency(entry.monthly_volume_usdt)}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Segunda fila */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                {/* Top Clientes */}
                <div className="card-glass p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-xl font-bold text-white flex items-center gap-2">
                            <Users className="w-5 h-5 text-purple-400" />
                            Top 5 Clientes
                        </h2>
                        <button className="text-sm text-blue-400 hover:text-blue-300">Ver todos →</button>
                    </div>
                    <div className="space-y-4">
                        {topClients.length === 0 ? (
                            <p className="text-gray-400 text-center py-8">No hay clientes aún</p>
                        ) : (
                            topClients.map((client, index) => (
                                <div key={index} className="flex items-center gap-4 p-3 bg-white/5 rounded-xl hover:bg-white/10 transition-all">
                                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-bold">
                                        {client.name?.charAt(0) || '?'}
                                    </div>
                                    <div className="flex-1">
                                        <p className="font-medium text-white">{client.name || 'Sin nombre'}</p>
                                        <p className="text-sm text-gray-400">{client.total_orders} órdenes</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="font-bold text-green-400">{formatCurrency(client.total_volume_usdt)}</p>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Órdenes en Cola */}
                <div className="card-glass p-6">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-xl font-bold text-white flex items-center gap-2">
                            <Clock className="w-5 h-5 text-cyan-400" />
                            Órdenes en Cola
                        </h2>
                        <button className="btn-primary text-sm py-2 px-4">
                            + Nueva Orden
                        </button>
                    </div>
                    <div className="space-y-3">
                        {orderQueue.length === 0 ? (
                            <p className="text-gray-400 text-center py-8">No hay órdenes pendientes</p>
                        ) : (
                            orderQueue.map((order, index) => (
                                <div key={index} className="flex items-center gap-4 p-4 bg-white/5 rounded-xl hover:bg-white/10 transition-all">
                                    <div className="flex items-center gap-2">
                                        <span className="text-xl">{countryFlags[order.origin_country] || '🌍'}</span>
                                        <span className="text-gray-400">→</span>
                                        <span className="text-xl">{countryFlags[order.dest_country] || '🌍'}</span>
                                    </div>
                                    <div className="flex-1">
                                        <p className="font-medium text-white">{order.client_name}</p>
                                        <p className="text-sm text-gray-400">#{order.public_id}</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="font-bold text-white">{formatCurrency(order.amount_origin)}</p>
                                        <span className={`badge ${getStatusColor(order.status)}`}>
                                            {order.status}
                                        </span>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>

            {/* Acciones Rápidas */}
            <div className="card-glass p-6">
                <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                    <Target className="w-5 h-5 text-blue-400" />
                    Acciones Rápidas
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <button className="p-6 bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl hover:from-blue-500 hover:to-blue-600 transition-all group">
                        <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                            <Wallet className="w-6 h-6 text-white" />
                        </div>
                        <p className="font-bold text-white">Nueva Orden</p>
                        <p className="text-sm text-blue-200">Crear envío</p>
                    </button>

                    <button className="p-6 bg-gradient-to-br from-green-600 to-green-700 rounded-xl hover:from-green-500 hover:to-green-600 transition-all group">
                        <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                            <Users className="w-6 h-6 text-white" />
                        </div>
                        <p className="font-bold text-white">Agregar Cliente</p>
                        <p className="text-sm text-green-200">Nuevo contacto</p>
                    </button>

                    <button className="p-6 bg-gradient-to-br from-purple-600 to-purple-700 rounded-xl hover:from-purple-500 hover:to-purple-600 transition-all group">
                        <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                            <TrendingUp className="w-6 h-6 text-white" />
                        </div>
                        <p className="font-bold text-white">Ver Tasas</p>
                        <p className="text-sm text-purple-200">Cotizaciones</p>
                    </button>

                    <button
                        onClick={() => router.push('/ranking')}
                        className="p-6 bg-gradient-to-br from-cyan-600 to-cyan-700 rounded-xl hover:from-cyan-500 hover:to-cyan-600 transition-all group"
                    >
                        <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                            <Trophy className="w-6 h-6 text-white" />
                        </div>
                        <p className="font-bold text-white">Mi Ranking</p>
                        <p className="text-sm text-cyan-200">Ver posición</p>
                    </button>

                    <button
                        onClick={() => router.push('/billetera')}
                        className="p-6 bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-xl hover:from-indigo-500 hover:to-indigo-600 transition-all group"
                    >
                        <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                            <Wallet className="w-6 h-6 text-white" />
                        </div>
                        <p className="font-bold text-white">Retirar</p>
                        <p className="text-sm text-indigo-200">Cobrar ganancias</p>
                    </button>
                </div>
            </div>
        </div>
    );
}
