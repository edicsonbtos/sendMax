"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";

export default function NuevoClientePage() {
    const router = useRouter();
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    // Form state
    const [fullName, setFullName] = useState("");
    const [paymentMethod, setPaymentMethod] = useState("Zelle");
    const [accountNumber, setAccountNumber] = useState("");
    const [bankName, setBankName] = useState("");
    const [country, setCountry] = useState("Venezuela");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setSuccess("");
        setSubmitting(true);

        try {
            await api.post("/api/operators/beneficiaries", {
                full_name: fullName,
                payment_method: paymentMethod,
                account_number: accountNumber,
                bank_name: bankName,
                country: country,
            });

            setSuccess("Cliente guardado exitosamente");

            // Redirigir después de 1.5 segundos
            setTimeout(() => {
                router.push("/clientes");
            }, 1500);
        } catch (err: unknown) {
            const errorMsg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Error al guardar el contacto";
            setError(errorMsg);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="p-8 max-w-4xl mx-auto space-y-6 animate-slide-up">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-white mb-2">Nuevo Cliente</h1>
                <p className="text-white/60">Agrega un nuevo contacto a tu agenda</p>
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

            {/* Formulario */}
            <form onSubmit={handleSubmit} className="card-glass p-6 space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Nombre completo */}
                    <div className="md:col-span-2">
                        <label className="block text-white/80 text-sm font-medium mb-2">
                            Nombre Completo *
                        </label>
                        <input
                            type="text"
                            required
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
                            placeholder="Juan Pérez"
                        />
                    </div>

                    {/* Método de pago */}
                    <div>
                        <label className="block text-white/80 text-sm font-medium mb-2">
                            Método de Pago *
                        </label>
                        <select
                            value={paymentMethod}
                            onChange={(e) => setPaymentMethod(e.target.value)}
                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
                        >
                            <option value="Zelle">Zelle</option>
                            <option value="Bank Transfer">Transferencia Bancaria</option>
                            <option value="Cash">Efectivo</option>
                            <option value="Pago Móvil">Pago Móvil</option>
                            <option value="Binance">Binance</option>
                        </select>
                    </div>

                    {/* País */}
                    <div>
                        <label className="block text-white/80 text-sm font-medium mb-2">
                            País *
                        </label>
                        <select
                            value={country}
                            onChange={(e) => setCountry(e.target.value)}
                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
                        >
                            <option value="Venezuela">Venezuela</option>
                            <option value="Colombia">Colombia</option>
                            <option value="Perú">Perú</option>
                            <option value="Argentina">Argentina</option>
                            <option value="México">México</option>
                            <option value="USA">USA</option>
                        </select>
                    </div>

                    {/* Número de cuenta */}
                    <div>
                        <label className="block text-white/80 text-sm font-medium mb-2">
                            Número de Cuenta / Teléfono *
                        </label>
                        <input
                            type="text"
                            required
                            value={accountNumber}
                            onChange={(e) => setAccountNumber(e.target.value)}
                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
                            placeholder="0412-1234567 o cuenta bancaria"
                        />
                    </div>

                    {/* Banco */}
                    <div>
                        <label className="block text-white/80 text-sm font-medium mb-2">
                            Banco (Opcional)
                        </label>
                        <input
                            type="text"
                            value={bankName}
                            onChange={(e) => setBankName(e.target.value)}
                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
                            placeholder="Nombre del banco"
                        />
                    </div>
                </div>

                {/* Botones */}
                <div className="flex gap-4 pt-4">
                    <button
                        type="button"
                        onClick={() => router.push("/clientes")}
                        className="flex-1 py-3 bg-white/5 hover:bg-white/10 text-white border border-white/10 font-medium rounded-xl transition-all"
                    >
                        Cancelar
                    </button>
                    <button
                        type="submit"
                        disabled={submitting}
                        className="flex-1 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
                    >
                        {submitting ? "Guardando..." : "Guardar Cliente"}
                    </button>
                </div>
            </form>
        </div>
    );
}
