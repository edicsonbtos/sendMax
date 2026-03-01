"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";

type RankingEntry = {
    position: number;
    user_id: number;
    alias: string;
    trust_score: number;
    total_orders: number;
    monthly_volume_usdt: number;
};

export default function RankingWidget() {
    const [ranking, setRanking] = useState<RankingEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchRanking = () => {
        api.get("/api/ranking/operators?limit=10")
            .then(res => {
                setRanking(res.data || []);
                setError(null);
            })
            .catch(err => {
                console.error("Error fetching ranking:", err);
                setError("Error al cargar ranking");
            })
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchRanking();
        const interval = setInterval(fetchRanking, 30000); // 30s polling
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col h-full">
            <h3 className="text-lg font-bold text-gray-800 mb-4">🏆 Grand Prix (Top 10)</h3>

            {loading && !ranking.length ? (
                <div className="flex-1 flex items-center justify-center">
                    <p className="text-gray-400 text-sm animate-pulse">Calculando posiciones...</p>
                </div>
            ) : error ? (
                <div className="flex-1 flex items-center justify-center">
                    <p className="text-red-500 text-sm bg-red-50 px-3 py-1 rounded">{error}</p>
                </div>
            ) : ranking.length === 0 ? (
                <div className="flex-1 flex items-center justify-center">
                    <p className="text-gray-500 text-sm">Aún no hay operadores rankeados</p>
                </div>
            ) : (
                <div className="overflow-y-auto pr-2">
                    <div className="space-y-4">
                        {ranking.map((op, idx) => (
                            <div key={op.user_id} className="flex items-center justify-between border-b border-gray-50 pb-2 last:border-0">
                                <div className="flex items-center gap-3">
                                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shadow-sm ${idx === 0 ? 'bg-yellow-100 text-yellow-600 border border-yellow-200' :
                                        idx === 1 ? 'bg-gray-100 text-gray-500 border border-gray-200' :
                                            idx === 2 ? 'bg-orange-100 text-orange-600 border border-orange-200' :
                                                'bg-slate-50 text-slate-400'
                                        }`}>
                                        {idx + 1}
                                    </div>
                                    <div>
                                        <p className="font-semibold text-sm text-gray-800">{op.alias || `Op #${op.user_id}`}</p>
                                        <p className="text-xs text-gray-400">{op.trust_score} pts • {op.total_orders} orders</p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className="font-bold text-sm text-green-600">${Number(op.monthly_volume_usdt).toFixed(0)}</p>
                                    <p className="text-[10px] text-gray-400 uppercase">Volumen</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
