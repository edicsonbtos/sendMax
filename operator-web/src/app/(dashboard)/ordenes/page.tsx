"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api"; // FIXED: Corregir el cliente falso destructurado apiGet
import { safeToFixed } from '@/lib/utils';

interface Order {
    id?: string;
    public_id: number;
    beneficiary_text?: string;
    beneficiary_name?: string;
    amount_origin?: number;
    amount_usd?: number;
    status: string;
    created_at: string;
    payment_method?: string;
}

export default function OrdenesPage() {
    const router = useRouter();
    const [orders, setOrders] = useState<Order[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<string>("all");

    useEffect(() => {
        loadOrders();
    }, []);

    const loadOrders = async () => {
        try {
            setLoading(true);
            const res = await api.get("/api/operators/orders"); // FIXED: Usar api.get
            setOrders(Array.isArray(res.data) ? res.data : []);
        } catch (error) {
            console.error("Error:", error);
        } finally {
            setLoading(false);
        }
    };

    const filteredOrders = orders.filter((o) => {
        if (filter === "all") return true;
        return o.status === filter;
    });

    const statusColors: Record<string, string> = {
        PENDING_APPROVAL: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
        APPROVED: "bg-green-500/20 text-green-400 border-green-500/30",
        COMPLETED: "bg-blue-500/20 text-blue-400 border-blue-500/30",
        REJECTED: "bg-red-500/20 text-red-400 border-red-500/30",
    };

    const statusLabels: Record<string, string> = {
        PENDING_APPROVAL: "Pendiente",
        APPROVED: "Aprobada",
        COMPLETED: "Completada",
        REJECTED: "Rechazada",
    };

    if (loading) {
        return (
            <div className="p-8 max-w-7xl mx-auto">
                <div className="card-glass p-6">
                    <p className="text-white">Cargando órdenes...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-6 animate-slide-up">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Órdenes</h1>
                    <p className="text-white/60">
                        {filteredOrders.length} orden{filteredOrders.length !== 1 ? "es" : ""}
                    </p>
                </div>
                <button
                    onClick={() => router.push("/ordenes/nueva")}
                    className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium rounded-xl transition-all transform hover:scale-105 shadow-lg"
                >
                    + Nueva Orden
                </button>
            </div>

            {/* Filtros */}
            <div className="card-glass p-4">
                <div className="flex gap-3">
                    {[
                        { key: "all", label: "Todas" },
                        { key: "PENDING_APPROVAL", label: "Pendientes" },
                        { key: "APPROVED", label: "Aprobadas" },
                        { key: "COMPLETED", label: "Completadas" },
                    ].map((f) => (
                        <button
                            key={f.key}
                            onClick={() => setFilter(f.key)}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${filter === f.key
                                ? "bg-blue-500 text-white"
                                : "bg-white/5 text-white/60 hover:bg-white/10"
                                }`}
                        >
                            {f.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Tabla */}
            <div className="card-glass p-6">
                {filteredOrders.length === 0 ? (
                    <div className="text-center py-12">
                        <p className="text-white/40 mb-4">No hay órdenes para mostrar</p>
                        <button
                            onClick={() => router.push("/ordenes/nueva")}
                            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                        >
                            Crear Primera Orden
                        </button>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-white/10">
                                    <th className="text-left text-white/60 text-sm font-medium py-3 px-4">
                                        Beneficiario
                                    </th>
                                    <th className="text-left text-white/60 text-sm font-medium py-3 px-4">
                                        Monto
                                    </th>
                                    <th className="text-left text-white/60 text-sm font-medium py-3 px-4">
                                        Método
                                    </th>
                                    <th className="text-left text-white/60 text-sm font-medium py-3 px-4">
                                        Estado
                                    </th>
                                    <th className="text-left text-white/60 text-sm font-medium py-3 px-4">
                                        Fecha
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredOrders.map((order) => (
                                    <tr
                                        key={order.public_id || order.id}
                                        className="border-b border-white/5 hover:bg-white/5 transition-colors cursor-pointer"
                                        onClick={() => router.push(`/ordenes/${order.public_id || order.id}`)}
                                    >
                                        <td className="py-4 px-4 text-white font-medium">
                                            {order.beneficiary_text || order.beneficiary_name || `Orden #${order.public_id}`}
                                        </td>
                                        <td className="py-4 px-4 text-white font-medium">
                                            ${safeToFixed(order.amount_origin ?? order.amount_usd, 2)} {/* FIXED: Number() para strings del backend */}
                                        </td>
                                        <td className="py-4 px-4 text-white/80 text-sm">
                                            {order.payment_method || 'Transferencia'}
                                        </td>
                                        <td className="py-4 px-4">
                                            <span
                                                className={`px-2.5 py-1 rounded-full text-xs font-medium border ${statusColors[order.status] ||
                                                    "bg-gray-500/20 text-gray-400"
                                                    }`}
                                            >
                                                {statusLabels[order.status] || order.status}
                                            </span>
                                        </td>
                                        <td className="py-4 px-4 text-white/60 text-sm">
                                            {new Date(order.created_at).toLocaleDateString("es-ES")}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
