"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import api from "@/lib/api";
import { safeToFixed } from "@/lib/utils";

interface OrderDetail {
    public_id: number;
    status: string;
    created_at: string;
    origin_country: string;
    amount_origin: number;
    client_name: string;
    dest_country: string;
    amount_dest: number;
    beneficiary_text: string;
    notes: string | null;
}

export default function OrderDetailPage() {
    const { id } = useParams();
    const router = useRouter();
    const [order, setOrder] = useState<OrderDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        if (id) {
            loadOrderDetail();
        }
    }, [id]);

    const loadOrderDetail = async () => {
        try {
            setLoading(true);
            const res = await api.get(`/api/operators/orders/${id}`);
            setOrder(res.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || "Error al cargar la orden");
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="p-8 max-w-4xl mx-auto">
                <div className="card-glass p-6 text-center">
                    <p className="text-white">Cargando detalles...</p>
                </div>
            </div>
        );
    }

    if (error || !order) {
        return (
            <div className="p-8 max-w-4xl mx-auto space-y-4">
                <button
                    onClick={() => router.push("/ordenes")}
                    className="text-white/60 hover:text-white flex items-center gap-2 transition-colors"
                >
                    ← Volver a Órdenes
                </button>
                <div className="card-glass p-6 border-l-4 border-red-500 bg-red-500/10">
                    <p className="text-red-400">{error || "Orden no encontrada"}</p>
                </div>
            </div>
        );
    }

    const statusColors: Record<string, string> = {
        PENDING_APPROVAL: "yellow",
        APPROVED: "green",
        COMPLETED: "blue",
        REJECTED: "red",
    };

    const statusLabels: Record<string, string> = {
        PENDING_APPROVAL: "Pendiente",
        APPROVED: "Aprobada",
        COMPLETED: "Completada",
        REJECTED: "Rechazada",
    };

    const statusColor = statusColors[order.status] || "gray";
    const statusText = statusLabels[order.status] || order.status;

    return (
        <div className="p-8 max-w-4xl mx-auto space-y-6 animate-slide-up">
            {/* Header / Back */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <button
                        onClick={() => router.push("/ordenes")}
                        className="text-white/60 hover:text-white flex items-center gap-2 mb-4 transition-colors"
                    >
                        ← Volver a Lista
                    </button>
                    <h1 className="text-3xl font-bold text-white mb-1">
                        Orden #{order.public_id}
                    </h1>
                    <p className="text-white/60 text-sm">
                        Creada el {new Date(order.created_at).toLocaleString()}
                    </p>
                </div>
                <div className={`px-4 py-2 rounded-full border border-${statusColor}-500/30 bg-${statusColor}-500/10 text-${statusColor}-400 font-medium whitespace-nowrap`}>
                    {statusText}
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Origen Box */}
                <div className="card-glass p-6 space-y-4">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400">
                            ↑
                        </div>
                        <div>
                            <p className="text-white/60 text-sm font-medium">Origen ({order.origin_country})</p>
                            <p className="text-white font-bold text-xl">
                                ${safeToFixed(order.amount_origin, 2)}
                            </p>
                        </div>
                    </div>

                    <div className="pt-4 border-t border-white/10">
                        <p className="text-white/40 text-xs uppercase mb-1">Enviado por</p>
                        <p className="text-white font-medium">{order.client_name}</p>
                    </div>
                </div>

                {/* Destino Box */}
                <div className="card-glass p-6 space-y-4">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center text-green-400">
                            ↓
                        </div>
                        <div>
                            <p className="text-white/60 text-sm font-medium">Destino ({order.dest_country})</p>
                            <p className="text-white font-bold text-xl">
                                {safeToFixed(order.amount_dest, 2)}
                            </p>
                        </div>
                    </div>

                    <div className="pt-4 border-t border-white/10">
                        <p className="text-white/40 text-xs uppercase mb-1">Recibe Beneficiario</p>
                        <p className="text-white font-medium">{order.beneficiary_text}</p>
                    </div>
                </div>
            </div>

            {/* Notes Section if any */}
            {order.notes && (
                <div className="card-glass p-6">
                    <h3 className="text-white/80 font-medium mb-2">Notas de la Orden</h3>
                    <p className="text-white/60 whitespace-pre-wrap">{order.notes}</p>
                </div>
            )}
        </div>
    );
}
