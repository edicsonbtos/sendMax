"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";

type Client = {
    name: string;
    total_volume_usdt: number;
    total_orders: number;
};

export default function TopClientsWidget() {
    const [clients, setClients] = useState<Client[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchClients = () => {
        api.get("/api/operators/dashboard/top-clients?limit=5")
            .then(res => {
                setClients(res.data || []);
                setError(null);
            })
            .catch(err => {
                console.error("Error fetching top clients:", err);
                setError("Error al cargar favoritos");
            })
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchClients();
        const interval = setInterval(fetchClients, 30000); // 30s polling
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col h-full bg-gradient-to-br from-white to-blue-50/30">
            <h3 className="text-lg font-bold text-gray-800 mb-4">🌟 Tus Top VIPs</h3>

            {loading && !clients.length ? (
                <div className="flex-1 flex items-center justify-center">
                    <p className="text-gray-400 text-sm animate-pulse">Buscando fidelidad...</p>
                </div>
            ) : error ? (
                <div className="flex-1 flex items-center justify-center">
                    <p className="text-red-500 text-sm bg-red-50 px-3 py-1 rounded">{error}</p>
                </div>
            ) : clients.length === 0 ? (
                <div className="flex-1 flex items-center justify-center">
                    <p className="text-gray-500 text-sm font-medium">Aún no hay clientes recurrentes</p>
                </div>
            ) : (
                <div className="space-y-4">
                    {clients.map((client, idx) => (
                        <div key={idx} className="flex items-center justify-between p-2 hover:bg-white rounded-lg transition-colors border border-transparent hover:border-blue-100 hover:shadow-sm">
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-full bg-[#0052FF]/10 text-[#0052FF] flex items-center justify-center font-bold text-sm">
                                    {client.name.charAt(0).toUpperCase()}
                                </div>
                                <div>
                                    <p className="font-semibold text-gray-800 text-sm truncate max-w-[120px]">{client.name}</p>
                                    <p className="text-xs text-gray-500">{client.total_orders} envíos exitosos</p>
                                </div>
                            </div>
                            <div className="text-right">
                                <p className="text-sm font-bold text-gray-900">${Number(client.total_volume_usdt).toFixed(0)}</p>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
