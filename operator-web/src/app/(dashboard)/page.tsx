"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import LiveRatesWidget from '@/components/dashboard/LiveRatesWidget';
import RankingWidget from '@/components/dashboard/RankingWidget';
import OrderQueueWidget from '@/components/dashboard/OrderQueueWidget';
import TopClientsWidget from '@/components/dashboard/TopClientsWidget';

export default function DashboardPage() {
    const [data, setData] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();

    useEffect(() => {
        api.get('/api/operators/dashboard/stats')
            .then(res => {
                setData(res.data);
                setError(null);
            })
            .catch(err => {
                console.error(err);
                setError(err.response?.data?.detail || err.message || "Error de red");
            })
            .finally(() => {
                setLoading(false);
            });
    }, []);

    const handleLogout = () => {
        localStorage.removeItem("auth_token");
        router.push("/login");
    };

    return (
        <div className="min-h-screen bg-[#F5F7FA] p-8">
            <div className="max-w-7xl mx-auto">
                <div className="flex justify-between items-center mb-8">
                    <h1 className="text-2xl font-bold text-[#0052FF]">Panel de Operador</h1>
                    <button
                        onClick={handleLogout}
                        className="px-4 py-2 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg text-sm font-medium transition-colors"
                    >
                        Cerrar Sesión
                    </button>
                </div>

                {loading && (
                    <div className="flex items-center justify-center p-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0052FF]"></div>
                    </div>
                )}

                {error && (
                    <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-6 shadow-sm border border-red-100">
                        {error}
                    </div>
                )}

                {data && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                        {/* Volumen Diario */}
                        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                            <p className="text-sm text-gray-500 font-medium mb-1">Volumen Diario</p>
                            <h3 className="text-2xl font-bold text-gray-900">${Number(data.daily_volume_usdt).toFixed(2)}</h3>
                            <p className="text-xs text-green-600 font-medium mt-2 bg-green-50 w-fit px-2 py-1 rounded">Hoy</p>
                        </div>

                        {/* Volumen Mensual */}
                        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                            <p className="text-sm text-gray-500 font-medium mb-1">Volumen Mensual</p>
                            <h3 className="text-2xl font-bold text-gray-900">${Number(data.monthly_volume_usdt).toFixed(2)}</h3>
                            <p className="text-xs text-blue-600 font-medium mt-2 bg-blue-50 w-fit px-2 py-1 rounded">Este mes</p>
                        </div>

                        {/* Órdenes */}
                        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                            <p className="text-sm text-gray-500 font-medium mb-1">Órdenes Activas</p>
                            <h3 className="text-2xl font-bold text-gray-900">{data.pending_orders} <span className="text-gray-400 text-lg font-normal">/ {data.total_orders}</span></h3>
                            <p className="text-xs text-orange-600 font-medium mt-2 bg-orange-50 w-fit px-2 py-1 rounded">Pendientes</p>
                        </div>

                        {/* Trust Score & Rank */}
                        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                            <p className="text-sm text-gray-500 font-medium mb-1">Confianza / Rank</p>
                            <div className="flex items-baseline gap-2">
                                <h3 className="text-2xl font-bold text-[#0052FF]">{Number(data.trust_score).toFixed(0)}</h3>
                                <span className="text-gray-400 text-sm">puntos</span>
                            </div>
                            <p className="text-xs text-purple-600 font-medium mt-2 bg-purple-50 w-fit px-2 py-1 rounded">
                                Top #{data.rank_position || "N/A"}
                            </p>
                        </div>
                    </div>
                )}

                {/* 2x2 Widgets Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <LiveRatesWidget />
                    <RankingWidget />
                    <OrderQueueWidget />
                    <TopClientsWidget />
                </div>
            </div>
        </div>
    );
}
