"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { safeToFixed } from '@/lib/utils';

interface Beneficiary {
    id: number;
    full_name: string;
    payment_method: string;
    account_number: string;
    bank_name?: string;
}

interface Client {
    id: number;
    full_name: string;
    phone: string | null;
    total_orders: number;
}

export default function NuevaOrdenPage() {
    const router = useRouter();
    const [beneficiaries, setBeneficiaries] = useState<Beneficiary[]>([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);

    // Form state
    const [selectedBeneficiary, setSelectedBeneficiary] = useState<number | null>(null);
    const [amount, setAmount] = useState("");
    const [paymentMethod, setPaymentMethod] = useState("Zelle");
    const [notes, setNotes] = useState("");
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    // Client states
    const [clientSearch, setClientSearch] = useState("");
    const [clientResults, setClientResults] = useState<Client[]>([]);
    const [selectedClient, setSelectedClient] = useState<Client | null>(null);
    const [showCreateClient, setShowCreateClient] = useState(false);
    const [newClientPhone, setNewClientPhone] = useState("");

    useEffect(() => {
        loadBeneficiaries();
    }, []);

    // Buscar clientes con debounce
    useEffect(() => {
        const timer = setTimeout(() => {
            if (clientSearch.length >= 2) {
                api.get(`/api/operators/clients/search?q=${clientSearch}`)
                    .then(res => setClientResults(res.data))
                    .catch(() => setClientResults([]));
            } else {
                setClientResults([]);
            }
        }, 300);
        return () => clearTimeout(timer);
    }, [clientSearch]);

    // Crear cliente rápido
    const handleCreateQuickClient = async () => {
        try {
            const res = await api.post("/api/operators/clients/", {
                full_name: clientSearch,
                phone: newClientPhone
            });
            setSelectedClient(res.data);
            setShowCreateClient(false);
            setClientSearch("");
            setClientResults([]);
        } catch (err: any) {
            setError(err.response?.data?.detail || "Error al crear cliente");
        }
    };

    const loadBeneficiaries = async () => {
        try {
            setLoading(true);
            const res = await api.get("/api/operators/beneficiaries");
            setBeneficiaries(res.data?.beneficiaries || []);
        } catch {
            setError("Error cargando contactos");
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setSuccess("");

        if (!selectedClient) {
            setError("Selecciona el cliente que envía el dinero");
            return;
        }

        if (!selectedBeneficiary) {
            setError("Selecciona un contacto / beneficiario");
            return;
        }

        setSubmitting(true);

        try {
            const response = await api.post("/api/operators/orders/create", {
                client_id: selectedClient.id,
                beneficiary_id: selectedBeneficiary,
                amount_usd: parseFloat(amount),
                payment_method: paymentMethod,
                notes: notes,
            });

            setSuccess(response.data?.message || "Orden creada exitosamente");

            // Redirigir a lista de órdenes después de 2 segundos
            setTimeout(() => {
                router.push("/ordenes");
            }, 2000);
        } catch (error) {
            setError((error as Error).message || "Error al crear la orden");
        } finally {
            setSubmitting(false);
        }
    };

    const selectedBeneficiaryData = beneficiaries.find(
        (b) => b.id === selectedBeneficiary
    );

    if (loading) {
        return (
            <div className="p-8 max-w-7xl mx-auto">
                <div className="card-glass p-6">
                    <p className="text-white">Cargando...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-8 max-w-4xl mx-auto space-y-6 animate-slide-up">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-white mb-2">Nueva Orden</h1>
                <p className="text-white/60">Crea una nueva orden de envío</p>
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
                    <p className="text-white/60 text-sm mt-1">Redirigiendo...</p>
                </div>
            )}

            {/* Formulario */}
            <form onSubmit={handleSubmit} className="card-glass p-6 space-y-6">

                {/* PASO 1: Seleccionar Cliente */}
                <div className="space-y-4">
                    <label className="block text-white/80 text-sm font-medium">
                        👤 ¿Quién te envía el dinero? (Cliente)
                    </label>

                    {selectedClient ? (
                        <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-xl flex justify-between items-center">
                            <div>
                                <p className="text-white font-bold">{selectedClient.full_name}</p>
                                <p className="text-white/60 text-sm">{selectedClient.phone || 'Sin teléfono'}</p>
                                <p className="text-green-400 text-xs">{selectedClient.total_orders} órdenes previas</p>
                            </div>
                            <button type="button" onClick={() => setSelectedClient(null)} className="text-red-400 hover:text-red-300">
                                ✕ Cambiar
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            <input
                                type="text"
                                value={clientSearch}
                                onChange={(e) => setClientSearch(e.target.value)}
                                placeholder="Buscar por nombre o teléfono..."
                                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                            />

                            {clientResults.length > 0 && (
                                <div className="bg-white/5 rounded-xl border border-white/10 divide-y divide-white/10 max-h-48 overflow-y-auto">
                                    {clientResults.map(client => (
                                        <div
                                            key={client.id}
                                            onClick={() => { setSelectedClient(client); setClientSearch(""); setClientResults([]); setShowCreateClient(false); }}
                                            className="p-4 hover:bg-white/10 cursor-pointer"
                                        >
                                            <p className="text-white font-medium">{client.full_name}</p>
                                            <p className="text-white/60 text-sm">{client.phone || 'Sin teléfono'} • {client.total_orders} órdenes</p>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {clientSearch.length >= 2 && clientResults.length === 0 && !showCreateClient && (
                                <button
                                    type="button"
                                    onClick={() => setShowCreateClient(true)}
                                    className="w-full p-4 border-2 border-dashed border-blue-500/50 rounded-xl text-blue-400 hover:bg-blue-500/10 transition-colors text-left pl-4"
                                >
                                    ➕ Crear nuevo cliente "{clientSearch}"
                                </button>
                            )}

                            {showCreateClient && (
                                <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl space-y-3 mt-2">
                                    <p className="text-white font-medium">Nuevo Cliente: {clientSearch}</p>
                                    <input
                                        type="text"
                                        value={newClientPhone}
                                        onChange={(e) => setNewClientPhone(e.target.value)}
                                        placeholder="Teléfono (Opcional)"
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                                    />
                                    <div className="flex gap-2 mt-2">
                                        <button type="button" onClick={handleCreateQuickClient} className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors font-medium">Guardar y Seleccionar</button>
                                        <button type="button" onClick={() => setShowCreateClient(false)} className="px-4 py-2 border border-white/10 text-white hover:bg-white/10 rounded-lg font-medium transition-colors">Cancelar</button>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Seleccionar beneficiario */}
                <div>
                    <label className="block text-white/80 text-sm font-medium mb-3">
                        Contacto / Beneficiario
                    </label>

                    {beneficiaries.length === 0 ? (
                        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
                            <p className="text-yellow-400 text-sm">
                                No tienes contactos guardados.
                            </p>
                            <button
                                type="button"
                                onClick={() => router.push("/clientes/nuevo")}
                                className="mt-2 text-blue-400 hover:text-blue-300 text-sm underline"
                            >
                                Crear primer contacto
                            </button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 gap-3">
                            {beneficiaries.map((b) => (
                                <div
                                    key={b.id}
                                    onClick={() => setSelectedBeneficiary(b.id)}
                                    className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${selectedBeneficiary === b.id
                                        ? "border-blue-500 bg-blue-500/10"
                                        : "border-white/10 bg-white/5 hover:border-white/20"
                                        }`}
                                >
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="text-white font-medium">{b.full_name}</p>
                                            <p className="text-white/60 text-sm">
                                                {b.payment_method} • {b.account_number}
                                            </p>
                                            {b.bank_name && (
                                                <p className="text-white/40 text-xs">{b.bank_name}</p>
                                            )}
                                        </div>
                                        {selectedBeneficiary === b.id && (
                                            <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center">
                                                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                </svg>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Monto */}
                <div>
                    <label className="block text-white/80 text-sm font-medium mb-2">
                        Monto (USD)
                    </label>
                    <input
                        type="number"
                        step="0.01"
                        min="0.01"
                        max="10000"
                        required
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white text-lg font-medium focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
                        placeholder="0.00"
                    />
                    <p className="text-white/40 text-xs mt-1">
                        Máximo: $10,000 USD por orden
                    </p>
                </div>

                {/* Método de pago */}
                <div>
                    <label className="block text-white/80 text-sm font-medium mb-2">
                        Método de Pago
                    </label>
                    <select
                        value={paymentMethod}
                        onChange={(e) => setPaymentMethod(e.target.value)}
                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
                    >
                        <option value="Zelle">Zelle</option>
                        <option value="Bank Transfer">Transferencia Bancaria</option>
                        <option value="Cash">Efectivo</option>
                        <option value="Crypto">Crypto</option>
                        <option value="PayPal">PayPal</option>
                    </select>
                </div>

                {/* Notas */}
                <div>
                    <label className="block text-white/80 text-sm font-medium mb-2">
                        Notas (Opcional)
                    </label>
                    <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
                        rows={3}
                        placeholder="Información adicional sobre la orden..."
                    />
                </div>

                {/* Resumen */}
                {selectedBeneficiaryData && amount && (
                    <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                        <p className="text-white/60 text-sm mb-2">Resumen de la orden:</p>
                        <div className="space-y-1">
                            <p className="text-white">
                                <span className="text-white/60">Para:</span>{" "}
                                {selectedBeneficiaryData.full_name}
                            </p>
                            <p className="text-white">
                                <span className="text-white/60">Monto:</span>{" "}
                                <span className="font-bold">${amount ? safeToFixed(amount, 2) : "0.00"} USD</span>
                            </p>
                            <p className="text-white">
                                <span className="text-white/60">Método:</span> {paymentMethod}
                            </p>
                        </div>
                    </div>
                )}

                {/* Botones */}
                <div className="flex gap-4">
                    <button
                        type="button"
                        onClick={() => router.push("/ordenes")}
                        className="flex-1 py-3 bg-white/5 hover:bg-white/10 text-white border border-white/10 font-medium rounded-xl transition-all"
                    >
                        Cancelar
                    </button>
                    <button
                        type="submit"
                        disabled={submitting || !selectedBeneficiary || !selectedClient || !amount}
                        className="flex-1 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
                    >
                        {submitting ? "Creando..." : "Crear Orden"}
                    </button>
                </div>
            </form>
        </div>
    );
}
