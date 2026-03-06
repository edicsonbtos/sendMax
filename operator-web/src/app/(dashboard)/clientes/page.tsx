'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from "@/lib/api";
import { safeToFixed } from '@/lib/utils';
import {
    Users,
    Plus,
    Search,
    Phone,
    Trophy,
    TrendingUp,
    Calendar,
    DollarSign,
    ShoppingCart
} from 'lucide-react';

interface ClientRanking {
    beneficiary_id: number;
    name: string;
    phone: string | null;
    dest_country: string;
    total_orders: number;
    completed_orders: number;
    total_volume_usdt: number;
    last_order_date: string | null;
    rank: number;
}

interface ClientStats {
    total_clients: number;
    active_clients: number;
    total_volume_usdt: number;
}

const COUNTRY_FLAGS: { [key: string]: string } = {
    'VENEZUELA': '🇻🇪',
    'COLOMBIA': '🇨🇴',
    'ARGENTINA': '🇦🇷',
    'CHILE': '🇨🇱',
    'PERU': '🇵🇪',
    'MEXICO': '🇲🇽',
    'ECUADOR': '🇪🇨',
};

export default function ClientesPage() {
    const router = useRouter();
    const [clients, setClients] = useState<ClientRanking[]>([]);
    const [stats, setStats] = useState<ClientStats | null>(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [rankingRes, statsRes] = await Promise.all([
                api.get('/api/operators/clients/ranking?limit=50'),
                api.get('/api/operators/clients/stats')
            ]);

            setClients(rankingRes.data || []);
            setStats(statsRes.data || null);
            setError(null);
        } catch (err: any) {
            console.error('Error cargando datos:', err);
            setError(err.message || 'Error al cargar clientes');
        } finally {
            setLoading(false);
        }
    };

    const filteredClients = clients.filter(c =>
        c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (c.phone && c.phone.includes(searchTerm))
    );

    const getRankBadge = (rank: number) => {
        if (rank === 1) return { icon: '🥇', color: 'from-yellow-400 to-yellow-600', text: 'TOP 1' };
        if (rank === 2) return { icon: '🥈', color: 'from-gray-300 to-gray-500', text: 'TOP 2' };
        if (rank === 3) return { icon: '🥉', color: 'from-orange-400 to-orange-600', text: 'TOP 3' };
        return { icon: `#${rank}`, color: 'from-blue-500 to-purple-500', text: `#${rank}` };
    };

    if (loading) {
        return (
            <div className="p-6 flex items-center justify-center min-h-screen">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-white/60">Cargando ranking de clientes...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6 animate-slide-up">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2 flex items-center gap-3">
                        <Trophy className="w-8 h-8 text-yellow-400" />
                        Leaderboard de Clientes
                    </h1>
                    <p className="text-white/60">Tus mejores clientes por volumen transaccionado</p>
                </div>
                <button
                    onClick={() => router.push('/clientes/nuevo')}
                    className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium rounded-xl transition-all shadow-lg flex items-center gap-2"
                >
                    <Plus className="w-5 h-5" />
                    Nuevo Cliente
                </button>
            </div>

            {/* Stats Cards */}
            {stats && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="card-glass p-6 border-l-4 border-blue-500">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-white/60 text-sm mb-1">Total Clientes</p>
                                <p className="text-3xl font-bold text-white">{stats.total_clients}</p>
                            </div>
                            <Users className="w-12 h-12 text-blue-400 opacity-50" />
                        </div>
                    </div>

                    <div className="card-glass p-6 border-l-4 border-green-500">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-white/60 text-sm mb-1">Clientes Activos</p>
                                <p className="text-3xl font-bold text-white">{stats.active_clients}</p>
                            </div>
                            <TrendingUp className="w-12 h-12 text-green-400 opacity-50" />
                        </div>
                    </div>

                    <div className="card-glass p-6 border-l-4 border-yellow-500">
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-white/60 text-sm mb-1">Volumen Total</p>
                                <p className="text-3xl font-bold text-white">${safeToFixed(stats.total_volume_usdt, 0)}</p>
                            </div>
                            <DollarSign className="w-12 h-12 text-yellow-400 opacity-50" />
                        </div>
                    </div>
                </div>
            )}

            {/* Error Message */}
            {error && (
                <div className="card-glass p-4 border-l-4 border-red-500 bg-red-500/10">
                    <p className="text-red-400">{error}</p>
                </div>
            )}

            {/* Búsqueda */}
            <div className="relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                <input
                    type="text"
                    placeholder="Buscar cliente por nombre o teléfono..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/40 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
                />
            </div>

            {/* Lista de Clientes */}
            {filteredClients.length === 0 ? (
                <div className="card-glass p-12 text-center">
                    <Users className="w-16 h-16 text-white/20 mx-auto mb-4" />
                    <h3 className="text-xl font-bold text-white mb-2">
                        {searchTerm ? 'No se encontraron clientes' : 'Sin clientes activos'}
                    </h3>
                    <p className="text-white/60 mb-6">
                        {searchTerm
                            ? 'Intenta con otro término de búsqueda'
                            : 'Los clientes aparecerán aquí después de completar su primera orden'}
                    </p>
                    {!searchTerm && (
                        <button
                            onClick={() => router.push('/clientes/nuevo')}
                            className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium rounded-xl transition-all shadow-lg inline-flex items-center gap-2"
                        >
                            <Plus className="w-5 h-5" />
                            Agregar Primer Cliente
                        </button>
                    )}
                </div>
            ) : (
                <div className="space-y-3">
                    {filteredClients.map((client) => {
                        const badge = getRankBadge(client.rank);
                        return (
                            <div
                                key={client.beneficiary_id}
                                className={`card-glass p-6 hover:scale-[1.02] transition-all cursor-pointer ${client.rank <= 3 ? 'border-2 border-yellow-500/30' : ''
                                    }`}
                                onClick={() => router.push(`/clientes/${client.beneficiary_id}`)}
                            >
                                <div className="flex items-center justify-between gap-4">
                                    {/* Ranking Badge */}
                                    <div className={`flex-shrink-0 w-16 h-16 rounded-xl bg-gradient-to-br ${badge.color} flex items-center justify-center text-white font-bold text-xl shadow-lg`}>
                                        {badge.icon}
                                    </div>

                                    {/* Info del Cliente */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h3 className="text-lg font-bold text-white truncate">{client.name}</h3>
                                            <span className="text-2xl">{COUNTRY_FLAGS[client.dest_country] || '🌍'}</span>
                                        </div>
                                        {client.phone && (
                                            <p className="text-white/60 text-sm flex items-center gap-2">
                                                <Phone className="w-4 h-4" />
                                                {client.phone}
                                            </p>
                                        )}
                                    </div>

                                    {/* Métricas */}
                                    <div className="flex gap-6 items-center">
                                        {/* Órdenes */}
                                        <div className="text-center">
                                            <div className="flex items-center gap-2 text-white/60 text-xs mb-1">
                                                <ShoppingCart className="w-4 h-4" />
                                                Órdenes
                                            </div>
                                            <p className="text-2xl font-bold text-white">{client.completed_orders}</p>
                                            <p className="text-xs text-white/40">de {client.total_orders}</p>
                                        </div>

                                        {/* Volumen */}
                                        <div className="text-center">
                                            <div className="flex items-center gap-2 text-green-400 text-xs mb-1">
                                                <DollarSign className="w-4 h-4" />
                                                Volumen
                                            </div>
                                            <p className="text-2xl font-bold text-green-400">${safeToFixed(client.total_volume_usdt, 0)}</p>
                                            <p className="text-xs text-white/40">USDT</p>
                                        </div>

                                        {/* Última orden */}
                                        {client.last_order_date && (
                                            <div className="text-center">
                                                <div className="flex items-center gap-2 text-white/60 text-xs mb-1">
                                                    <Calendar className="w-4 h-4" />
                                                    Última orden
                                                </div>
                                                <p className="text-sm text-white/80">
                                                    {new Date(client.last_order_date).toLocaleDateString('es-ES', {
                                                        day: '2-digit',
                                                        month: 'short'
                                                    })}
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
