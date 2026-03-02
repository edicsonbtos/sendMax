"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface Order {
    public_id: number;
    origin_country: string;
    dest_country: string;
    amount_origin: string; // Decimal comes as string or number
    payout_dest: string;
    status: string;
    created_at: string;
    beneficiary_text: string;
}

const statusColors: Record<string, string> = {
    'CREADA': 'bg-gray-100 text-gray-800',
    'ORIGEN_VERIFICANDO': 'bg-yellow-100 text-yellow-800',
    'ORIGEN_CONFIRMADO': 'bg-blue-100 text-blue-800',
    'PAGO_PENDIENTE': 'bg-orange-100 text-orange-800',
    'COMPLETADA': 'bg-green-100 text-green-800',
    'CANCELADA': 'bg-red-100 text-red-800',
};

export default function OrdenesPage() {
    const [orders, setOrders] = useState<Order[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [statusFilter, setStatusFilter] = useState("TODOS");

    useEffect(() => {
        const fetchOrders = async () => {
            setLoading(true);
            setError(null);
            try {
                const token = localStorage.getItem("operator_token");
                if (!token) throw new Error("No hay token de sesión");

                const queryParams = new URLSearchParams({
                    limit: "50",
                    ...(statusFilter !== "TODOS" && { status: statusFilter }),
                    ...(search && { q: search }),
                });

                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://sendmax11-production.up.railway.app";
                const res = await fetch(`${apiUrl}/api/operators/orders?${queryParams}`, {
                    headers: {
                        "Authorization": `Bearer ${token}`
                    }
                });

                if (!res.ok) {
                    throw new Error("Lamentablemente hubo un error al obtener las órdenes.");
                }

                const data = await res.json();
                setOrders(data);
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        const debounce = setTimeout(() => {
            fetchOrders();
        }, 300);

        return () => clearTimeout(debounce);
    }, [search, statusFilter]);

    return (
        <div className="p-8 max-w-7xl mx-auto">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-3xl font-black text-gray-900 tracking-tight">Órdenes</h1>
                <Link
                    href="/ordenes/nueva"
                    className="bg-[#0052FF] text-white px-6 py-2.5 rounded-lg font-semibold shadow-sm hover:bg-[#0040CC] transition-colors"
                >
                    Nueva Orden
                </Link>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-6">
                <div className="flex flex-col md:flex-row gap-4">
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-1">Buscar</label>
                        <input
                            type="text"
                            placeholder="Buscar por ID o Beneficiario..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#0052FF] focus:border-transparent outline-none transition-all"
                        />
                    </div>
                    <div className="w-full md:w-64">
                        <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
                        <select
                            value={statusFilter}
                            onChange={(e) => setStatusFilter(e.target.value)}
                            className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#0052FF] focus:border-transparent outline-none transition-all bg-white"
                        >
                            <option value="TODOS">Todos</option>
                            <option value="CREADA">Creada</option>
                            <option value="ORIGEN_VERIFICANDO">Origen Verificando</option>
                            <option value="ORIGEN_CONFIRMADO">Origen Confirmado</option>
                            <option value="PAGO_PENDIENTE">Pago Pendiente</option>
                            <option value="COMPLETADA">Completada</option>
                            <option value="CANCELADA">Cancelada</option>
                        </select>
                    </div>
                </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-gray-50 border-b border-gray-100">
                            <tr>
                                <th className="py-4 px-6 font-semibold text-gray-500 text-sm">ID</th>
                                <th className="py-4 px-6 font-semibold text-gray-500 text-sm">Ruta</th>
                                <th className="py-4 px-6 font-semibold text-gray-500 text-sm">Beneficiario</th>
                                <th className="py-4 px-6 font-semibold text-gray-500 text-sm text-right">Monto Origen</th>
                                <th className="py-4 px-6 font-semibold text-gray-500 text-sm text-right">Recibe</th>
                                <th className="py-4 px-6 font-semibold text-gray-500 text-sm text-center">Estado</th>
                                <th className="py-4 px-6 font-semibold text-gray-500 text-sm">Fecha</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {loading ? (
                                <tr>
                                    <td colSpan={7} className="py-8 text-center text-gray-500">
                                        <div className="flex items-center justify-center gap-3">
                                            <div className="w-5 h-5 border-2 border-t-[#0052FF] border-gray-200 rounded-full animate-spin"></div>
                                            Cargando órdenes...
                                        </div>
                                    </td>
                                </tr>
                            ) : error ? (
                                <tr>
                                    <td colSpan={7} className="py-8 text-center text-red-500">
                                        {error}
                                    </td>
                                </tr>
                            ) : orders.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="py-8 text-center text-gray-500">
                                        No se encontraron órdenes.
                                    </td>
                                </tr>
                            ) : (
                                orders.map((order) => (
                                    <tr key={order.public_id} className="hover:bg-gray-50/50 transition-colors">
                                        <td className="py-4 px-6 font-mono text-sm">#{order.public_id}</td>
                                        <td className="py-4 px-6">
                                            <div className="flex items-center gap-2 text-sm">
                                                <span className="font-medium text-gray-900">{order.origin_country}</span>
                                                <span className="text-gray-400">→</span>
                                                <span className="font-medium text-gray-900">{order.dest_country}</span>
                                            </div>
                                        </td>
                                        <td className="py-4 px-6 text-sm text-gray-600 truncate max-w-[150px]" title={order.beneficiary_text}>
                                            {order.beneficiary_text.length > 30 ? order.beneficiary_text.substring(0, 30) + '...' : order.beneficiary_text || 'Sin nombre'}
                                        </td>
                                        <td className="py-4 px-6 text-right font-medium text-gray-900">
                                            $ {Number(order.amount_origin).toFixed(2)}
                                        </td>
                                        <td className="py-4 px-6 text-right font-medium text-[#0052FF]">
                                            $ {Number(order.payout_dest).toFixed(2)}
                                        </td>
                                        <td className="py-4 px-6 text-center">
                                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[order.status] || 'bg-gray-100 text-gray-800'}`}>
                                                {order.status.replace('_', ' ')}
                                            </span>
                                        </td>
                                        <td className="py-4 px-6 text-sm text-gray-500">
                                            {new Date(order.created_at).toLocaleDateString()}
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
