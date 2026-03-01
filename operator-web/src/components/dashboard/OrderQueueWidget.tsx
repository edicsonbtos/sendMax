"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";

type OrderItem = {
    public_id: number;
    client_name: string;
    amount_origin: number;
    origin_country: string;
    dest_country: string;
    status: string;
    created_at: string;
};

export default function OrderQueueWidget() {
    const [orders, setOrders] = useState<OrderItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchOrders = () => {
        api.get("/api/operators/orders/queue")
            .then(res => {
                setOrders(res.data || []);
                setError(null);
            })
            .catch(err => {
                console.error("Error fetching orders:", err);
                setError("Error al cargar cola de trabajo");
            })
            .finally(() => setLoading(false));
    };

    useEffect(() => {
        fetchOrders();
        const interval = setInterval(fetchOrders, 30000); // 30s polling
        return () => clearInterval(interval);
    }, []);

    const getStatusColor = (status: string) => {
        if (status.includes("CREADA") || status.includes("VERIFICANDO")) {
            return "bg-yellow-50 text-yellow-700 border-yellow-200";
        }
        if (status.includes("CONFIRMADO") || status.includes("PENDIENTE")) {
            return "bg-blue-50 text-blue-700 border-blue-200";
        }
        if (status.includes("COMPLETADA")) {
            return "bg-green-50 text-green-700 border-green-200";
        }
        if (status.includes("CANCELADA") || status.includes("RECHAZADA")) {
            return "bg-red-50 text-red-700 border-red-200";
        }
        return "bg-gray-50 text-gray-700 border-gray-200";
    };

    return (
        <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col h-full col-span-1 lg:col-span-2">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-bold text-gray-800">⚡ Tu Cola de Trabajo</h3>
                <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded-full">
                    {orders.length} activas
                </span>
            </div>

            {loading && !orders.length ? (
                <div className="flex-1 flex items-center justify-center">
                    <p className="text-gray-400 text-sm animate-pulse">Obteniendo órdenes recientes...</p>
                </div>
            ) : error ? (
                <div className="flex-1 flex items-center justify-center">
                    <p className="text-red-500 text-sm bg-red-50 px-3 py-1 rounded">{error}</p>
                </div>
            ) : orders.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center py-8">
                    <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center border border-dashed border-gray-300 mb-3">
                        <span className="text-2xl opacity-50">🏖️</span>
                    </div>
                    <p className="text-gray-500 text-sm font-medium">Bandeja impecable</p>
                    <p className="text-gray-400 text-xs mt-1">No tienes órdenes pendientes en este momento</p>
                </div>
            ) : (
                <div className="overflow-x-auto w-full">
                    <table className="w-full text-sm text-left">
                        <thead className="text-xs text-gray-500 uppercase bg-gray-50 border-y">
                            <tr>
                                <th className="px-4 py-3 font-medium">ID #</th>
                                <th className="px-4 py-3 font-medium">Cliente</th>
                                <th className="px-4 py-3 font-medium">Ruta</th>
                                <th className="px-4 py-3 font-medium">Monto</th>
                                <th className="px-4 py-3 font-medium">Estado</th>
                                <th className="px-4 py-3 font-medium text-right">Tiempo</th>
                            </tr>
                        </thead>
                        <tbody>
                            {orders.map((o) => (
                                <tr key={o.public_id} className="border-b last:border-0 hover:bg-gray-50 transition-colors">
                                    <td className="px-4 py-3 font-semibold text-gray-900">#{o.public_id}</td>
                                    <td className="px-4 py-3 text-gray-700 truncate max-w-[150px]">{o.client_name}</td>
                                    <td className="px-4 py-3 text-xs text-gray-500">{o.origin_country} <span className="mx-1">→</span> {o.dest_country}</td>
                                    <td className="px-4 py-3 font-medium text-gray-900">{Number(o.amount_origin).toFixed(2)}</td>
                                    <td className="px-4 py-3">
                                        <span className={`px-2 py-1 text-xs border rounded-md font-medium whitespace-nowrap ${getStatusColor(o.status)}`}>
                                            {o.status.replace(/_/g, " ")}
                                        </span>
                                    </td>
                                    <td className="px-4 py-3 text-right text-xs text-gray-400 whitespace-nowrap">
                                        {formatDistanceToNow(new Date(o.created_at), { addSuffix: true, locale: es })}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
