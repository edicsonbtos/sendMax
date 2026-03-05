"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api"; // FIXED: Importar correctamente el cliente Axios default
import { safeToFixed } from '@/lib/utils';

interface WalletSummary {
    balance_usdt: number;
    total_earned: number;
    total_withdrawn: number;
    pending_withdrawals: number;
}

interface Withdrawal {
    id: string;
    amount: number;
    status: "pending" | "approved" | "rejected";
    method: string;
    account: string;
    created_at: string;
    description: string;
}

export default function BilleteraPage() {
    const [summary, setSummary] = useState<WalletSummary | null>(null);
    const [withdrawals, setWithdrawals] = useState<Withdrawal[]>([]);
    const [loading, setLoading] = useState(true);
    const [showWithdrawForm, setShowWithdrawForm] = useState(false);

    // Form state
    const [amount, setAmount] = useState("");
    const [method, setMethod] = useState("bank_transfer");
    const [account, setAccount] = useState("");
    const [notes, setNotes] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    useEffect(() => {
        loadData();
        // FIXED: Implementar auto-refresh en tiempo real cada 30 segundos
        const interval = setInterval(loadData, 30000);
        return () => clearInterval(interval);
    }, []);

    const loadData = async () => {
        try {
            setLoading(true);
            const [summaryRes, withdrawalsRes] = await Promise.all([
                api.get("/api/operators/wallet/summary"), // FIXED: Usar api.get() valido
                api.get("/api/operators/wallet/withdrawals"), // FIXED: Usar api.get() valido
            ]);

            setSummary(summaryRes.data);
            setWithdrawals(withdrawalsRes.data.withdrawals || []);
        } catch (err) {
            console.error("Error cargando datos:", err);
        } finally {
            setLoading(false);
        }
    };

    const handleSubmitWithdraw = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setSuccess("");
        setSubmitting(true);

        try {
            // FIXED: Usar api.post() del cliente real
            const response = await api.post("/api/operators/wallet/withdraw", {
                amount_usdt: parseFloat(amount),
                withdrawal_method: method,
                account_info: account,
                notes: notes,
            });

            setSuccess(response.data.message || "Retiro solicitado exitosamente");

            // Limpiar form
            setAmount("");
            setAccount("");
            setNotes("");
            setShowWithdrawForm(false);

            // Recargar datos
            setTimeout(loadData, 1000);
        } catch (err: unknown) {
            const errorMsg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || (err as Error).message || "Error al solicitar retiro";
            setError(errorMsg);
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="p-8 max-w-7xl mx-auto">
                <div className="card-glass p-6">
                    <p className="text-white">Cargando billetera...</p>
                </div>
            </div>
        );
    }

    const statusColors = {
        pending: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
        approved: "bg-green-500/20 text-green-400 border-green-500/30",
        rejected: "bg-red-500/20 text-red-400 border-red-500/30",
    };

    const statusLabels = {
        pending: "Pendiente",
        approved: "Aprobado",
        rejected: "Rechazado",
    };

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-6 animate-slide-up">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-white mb-2">Billetera</h1>
                    <p className="text-white/60">Gestiona tus fondos y retiros</p>
                </div>
                <button
                    onClick={() => setShowWithdrawForm(!showWithdrawForm)}
                    className="px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium rounded-xl transition-all transform hover:scale-105 shadow-lg"
                >
                    {showWithdrawForm ? "Cancelar" : "Solicitar Retiro"}
                </button>
            </div>

            {/* Mensajes */}
            {error && (
                <div className="card-glass p-4 border-l-4 border-red-500 bg-red-500/10">
                    <p className="text-red-400">{error}</p>
                </div>
            )}

            {success && (
                <div className="card-glass p-4 border-l-4 border-green-500 bg-green-500/10">
                    <p className="text-green-400">{success}</p>
                </div>
            )}

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="card-glass p-6">
                    <p className="text-white/60 text-sm mb-2">Balance Disponible</p>
                    <p className="text-3xl font-bold text-white">
                        ${safeToFixed(summary?.balance_usdt, 2)}
                    </p>
                    <p className="text-white/40 text-xs mt-1">USDT</p>
                </div>

                <div className="card-glass p-6">
                    <p className="text-white/60 text-sm mb-2">Total Ganado</p>
                    <p className="text-2xl font-bold text-green-400">
                        ${safeToFixed(summary?.total_earned, 2)}
                    </p>
                </div>

                <div className="card-glass p-6">
                    <p className="text-white/60 text-sm mb-2">Total Retirado</p>
                    <p className="text-2xl font-bold text-blue-400">
                        ${safeToFixed(summary?.total_withdrawn, 2)}
                    </p>
                </div>

                <div className="card-glass p-6">
                    <p className="text-white/60 text-sm mb-2">Retiros Pendientes</p>
                    <p className="text-2xl font-bold text-yellow-400">
                        ${safeToFixed(summary?.pending_withdrawals, 2)}
                    </p>
                </div>
            </div>

            {/* Formulario de retiro */}
            {showWithdrawForm && (
                <div className="card-glass p-6">
                    <h2 className="text-xl font-bold text-white mb-4">Solicitar Retiro</h2>
                    <form onSubmit={handleSubmitWithdraw} className="space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-white/80 text-sm mb-2">
                                    Monto (USDT)
                                </label>
                                <input
                                    type="number"
                                    step="0.01"
                                    min="0.01"
                                    required
                                    value={amount}
                                    onChange={(e) => setAmount(e.target.value)}
                                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
                                    placeholder="0.00"
                                />
                                <p className="text-white/40 text-xs mt-1">
                                    Disponible: ${safeToFixed(summary?.balance_usdt, 2)}
                                </p>
                            </div>

                            <div>
                                <label className="block text-white/80 text-sm mb-2">
                                    Método de Retiro
                                </label>
                                <select
                                    value={method}
                                    onChange={(e) => setMethod(e.target.value)}
                                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
                                >
                                    <option value="bank_transfer">Transferencia Bancaria</option>
                                    <option value="crypto_usdt">USDT (Crypto)</option>
                                    <option value="paypal">PayPal</option>
                                    <option value="zelle">Zelle</option>
                                    <option value="binance">Binance</option>
                                </select>
                            </div>
                        </div>

                        <div>
                            <label className="block text-white/80 text-sm mb-2">
                                Cuenta / Dirección
                            </label>
                            <input
                                type="text"
                                required
                                value={account}
                                onChange={(e) => setAccount(e.target.value)}
                                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
                                placeholder="Número de cuenta, dirección wallet, email, etc."
                            />
                        </div>

                        <div>
                            <label className="block text-white/80 text-sm mb-2">
                                Notas (Opcional)
                            </label>
                            <textarea
                                value={notes}
                                onChange={(e) => setNotes(e.target.value)}
                                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
                                rows={3}
                                placeholder="Información adicional..."
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={submitting}
                            className="w-full py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {submitting ? "Procesando..." : "Confirmar Retiro"}
                        </button>
                    </form>
                </div>
            )}

            {/* Historial de retiros */}
            <div className="card-glass p-6">
                <h2 className="text-xl font-bold text-white mb-4">Historial de Retiros</h2>

                {withdrawals.length === 0 ? (
                    <p className="text-white/40 text-center py-8">
                        No hay retiros registrados
                    </p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead>
                                <tr className="border-b border-white/10">
                                    <th className="text-left text-white/60 text-sm font-medium py-3 px-4">
                                        Fecha
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
                                        Descripción
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                {withdrawals.map((w) => (
                                    <tr
                                        key={w.id}
                                        className="border-b border-white/5 hover:bg-white/5 transition-colors"
                                    >
                                        <td className="py-4 px-4 text-white/80 text-sm">
                                            {new Date(w.created_at).toLocaleDateString("es-ES", {
                                                year: "numeric",
                                                month: "short",
                                                day: "numeric",
                                                hour: "2-digit",
                                                minute: "2-digit",
                                            })}
                                        </td>
                                        <td className="py-4 px-4 text-white font-medium">
                                            ${safeToFixed(w.amount, 2)}
                                        </td>
                                        <td className="py-4 px-4 text-white/80 text-sm">
                                            {w.method}
                                        </td>
                                        <td className="py-4 px-4">
                                            <span
                                                className={`px-2.5 py-1 rounded-full text-xs font-medium border ${statusColors[w.status]
                                                    }`}
                                            >
                                                {statusLabels[w.status]}
                                            </span>
                                        </td>
                                        <td className="py-4 px-4 text-white/60 text-sm">
                                            {w.description}
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
