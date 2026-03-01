"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";

type Rate = {
    origin: string;
    dest: string;
    rate: number;
    commission_pct: number;
};

export default function LiveRatesWidget() {
    const [rates, setRates] = useState<Rate[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchRates = () => {
        api.get("/api/rates/current")
            .then(res => {
                setRates(res.data.rates || []);
                setError(null);
            })
            .catch(err => {
                console.error("Error fetching rates:", err);
                setError("Error al cargar tasas");
            })
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchRates();
        const interval = setInterval(fetchRates, 30000); // 30s polling
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col h-full">
            <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                Tasas en Vivo
            </h3>

            {loading && !rates.length ? (
                <div className="flex-1 flex items-center justify-center">
                    <p className="text-gray-400 text-sm animate-pulse">Cargando tasas...</p>
                </div>
            ) : error ? (
                <div className="flex-1 flex items-center justify-center">
                    <p className="text-red-500 text-sm bg-red-50 px-3 py-1 rounded">{error}</p>
                </div>
            ) : rates.length === 0 ? (
                <div className="flex-1 flex items-center justify-center">
                    <p className="text-gray-500 text-sm">No hay tasas activas</p>
                </div>
            ) : (
                <div className="overflow-y-auto pr-2 custom-scrollbar">
                    <div className="space-y-3">
                        {rates.map((r, idx) => (
                            <div key={idx} className="flex justify-between items-center p-3 hover:bg-gray-50 rounded-lg border border-gray-50 transition-colors">
                                <div className="flex items-center gap-2">
                                    <span className="font-semibold text-gray-700">{r.origin}</span>
                                    <span className="text-gray-400 text-xs">→</span>
                                    <span className="font-semibold text-gray-700">{r.dest}</span>
                                </div>
                                <div className="text-right">
                                    <p className="font-bold text-[#0052FF]">{r.rate}</p>
                                    <p className="text-xs text-gray-400">Com. {r.commission_pct}%</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
