"use client";

import { useState, useEffect } from "react";

interface WalletSummary {
    balance_usdt: number;
    lifetime_earnings_usdt: number;
    pending_withdrawals_usdt: number;
}

interface LedgerItem {
    id: number;
    amount_usdt: number;
    type: string;
    description: string;
    created_at: string;
}

export default function BilleteraPage() {
    const [summary, setSummary] = useState<WalletSummary | null>(null);
    const [ledger, setLedger] = useState<LedgerItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [withdrawMessage, setWithdrawMessage] = useState("");

    useEffect(() => {
        const fetchWalletData = async () => {
            setLoading(true);
            setError(null);
            try {
                const token = localStorage.getItem("auth_token") || localStorage.getItem("operator_token");
                if (!token) {
                    window.location.href = "/login";
                    return;
                }

                const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
                const headers = { "Authorization": `Bearer ${token}` };

                const [resSummary, resLedger] = await Promise.all([
                    fetch(`${apiUrl}/api/operators/wallet/summary`, { headers }),
                    fetch(`${apiUrl}/api/operators/wallet/ledger?limit=50`, { headers })
                ]);

                if (resSummary.status === 401 || resLedger.status === 401) {
                    localStorage.removeItem("auth_token");
                    localStorage.removeItem("operator_token");
                    window.location.href = "/login";
                    return;
                }

                if (!resSummary.ok || !resLedger.ok) throw new Error("Error obteniendo datos de la billetera");

                setSummary(await resSummary.json());
                setLedger(await resLedger.json());
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchWalletData();
    }, []);

    const handleWithdraw = async () => {
        try {
            const token = localStorage.getItem("auth_token") || localStorage.getItem("operator_token");
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const res = await fetch(`${apiUrl}/api/operators/wallet/withdraw`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${token}` }
            });

            if (res.status === 401) {
                window.location.href = "/login";
                return;
            }

            if (res.status === 501) {
                setWithdrawMessage("Not implemented: El sistema de retiros automáticos aún está en desarrollo.");
            } else {
                setWithdrawMessage("Solicitud completada (o error no esperado).");
            }
        } catch (e) {
            setWithdrawMessage("Error de conexión al solicitar el retiro.");
        }
    };

    return (
        <div className="p-8 max-w-7xl mx-auto">
            <h1 className="text-3xl font-black text-gray-900 tracking-tight mb-8">Billetera</h1>

            {error && (
                <div className="bg-red-50 text-red-700 p-4 rounded-xl mb-6 border border-red-100 font-medium">
                    {error}
                </div>
            )}

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col justify-center items-center">
                    <p className="text-sm text-gray-500 font-medium mb-1">Saldo Disponible (USDT)</p>
                    {loading ? (
                        <div className="h-10 w-24 bg-gray-200 animate-pulse rounded"></div>
                    ) : (
                        <p className="text-4xl font-black text-[#0052FF]">${summary?.balance_usdt || 0}</p>
                    )}
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col justify-center items-center">
                    <p className="text-sm text-gray-500 font-medium mb-1">Ganancias Acumuladas</p>
                    {loading ? (
                        <div className="h-10 w-24 bg-gray-200 animate-pulse rounded"></div>
                    ) : (
                        <p className="text-4xl font-black text-green-500">${summary?.lifetime_earnings_usdt || 0}</p>
                    )}
                </div>
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 flex flex-col justify-center items-center">
                    <p className="text-sm text-gray-500 font-medium mb-1">Retiros Pendientes</p>
                    {loading ? (
                        <div className="h-10 w-24 bg-gray-200 animate-pulse rounded"></div>
                    ) : (
                        <p className="text-4xl font-black text-orange-500">${summary?.pending_withdrawals_usdt || 0}</p>
                    )}
                </div>
            </div>

            {/* Withdraw Action */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 mb-8 flex flex-col sm:flex-row items-center justify-between gap-4">
                <div>
                    <h3 className="text-lg font-bold text-gray-800">Retirar Fondos</h3>
                    <p className="text-sm text-gray-500">Solicita el retiro de tu saldo hacia tu wallet configurada.</p>
                </div>
                <button
                    onClick={handleWithdraw}
                    className="bg-[#0052FF] text-white px-8 py-3 rounded-lg font-semibold shadow-sm hover:bg-[#0040CC] transition-colors whitespace-nowrap"
                >
                    Solicitar Retiro
                </button>
            </div>

            {withdrawMessage && (
                <div className="bg-blue-50 text-blue-800 p-4 rounded-xl mb-8 border border-blue-100 font-medium">
                    {withdrawMessage}
                </div>
            )}

            {/* Ledger Table */}
            <h2 className="text-xl font-bold text-gray-800 tracking-tight mb-4">Últimos Movimientos</h2>
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-gray-50 border-b border-gray-100">
                            <tr>
                                <th className="py-4 px-6 font-semibold text-gray-500 text-sm">Fecha</th>
                                <th className="py-4 px-6 font-semibold text-gray-500 text-sm">Descripción</th>
                                <th className="py-4 px-6 font-semibold text-gray-500 text-sm text-center">Tipo</th>
                                <th className="py-4 px-6 font-semibold text-gray-500 text-sm text-right">Monto (USDT)</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {loading ? (
                                <tr>
                                    <td colSpan={4} className="py-8 text-center text-gray-500">
                                        <div className="flex items-center justify-center gap-3">
                                            <div className="w-5 h-5 border-2 border-t-[#0052FF] border-gray-200 rounded-full animate-spin"></div>
                                            Cargando movimientos...
                                        </div>
                                    </td>
                                </tr>
                            ) : ledger.length === 0 ? (
                                <tr>
                                    <td colSpan={4} className="py-12 flex flex-col items-center justify-center text-center">
                                        <span className="text-4xl mb-3">📭</span>
                                        <p className="text-gray-500 font-medium">No hay movimientos registrados aún.</p>
                                    </td>
                                </tr>
                            ) : (
                                ledger.map((item) => (
                                    <tr key={item.id} className="hover:bg-gray-50/50 transition-colors">
                                        <td className="py-4 px-6 text-sm text-gray-500">
                                            {new Date(item.created_at).toLocaleString()}
                                        </td>
                                        <td className="py-4 px-6 text-sm text-gray-800 max-w-[200px] truncate">
                                            {item.description}
                                        </td>
                                        <td className="py-4 px-6 text-center">
                                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${item.type === 'EARNING' ? 'bg-green-100 text-green-800' :
                                                    item.type.includes('WITHDRAWAL') ? 'bg-orange-100 text-orange-800' :
                                                        'bg-gray-100 text-gray-800'
                                                }`}>
                                                {item.type}
                                            </span>
                                        </td>
                                        <td className={`py-4 px-6 text-right font-bold ${Number(item.amount_usdt) > 0 ? 'text-green-500' : 'text-gray-900'
                                            }`}>
                                            {Number(item.amount_usdt) > 0 ? '+' : ''}{Number(item.amount_usdt).toFixed(2)}
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
