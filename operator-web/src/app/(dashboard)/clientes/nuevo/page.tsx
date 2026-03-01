"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import Link from "next/link";

export default function NuevoClientePage() {
    const router = useRouter();
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const [form, setForm] = useState({
        alias: "",
        full_name: "",
        dest_country: "VENEZUELA",
        bank_name: "",
        account_number: "",
        phone: "",
        payment_method: "",
        notes: ""
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        setForm({ ...form, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            await api.post("/api/operators/beneficiaries", form);
            router.push("/clientes"); // Redirige al success
        } catch (err: any) {
            if (err.response?.status === 401) {
                setError("Tu sesión expiró. Por favor, vuelve a iniciar sesión.");
            } else {
                setError(err.response?.data?.detail || "Error al crear beneficiario");
            }
            setLoading(false);
        }
    };

    return (
        <div className="max-w-3xl mx-auto">
            <div className="flex items-center gap-4 mb-6">
                <Link href="/clientes" className="text-gray-400 hover:text-[#0052FF] transition-colors">
                    ← Volver
                </Link>
                <h1 className="text-2xl font-bold text-gray-900">Agregar Contacto / Beneficiario</h1>
            </div>

            <form onSubmit={handleSubmit} className="bg-white p-6 md:p-8 rounded-xl shadow-sm border border-gray-100 space-y-6">
                {error && (
                    <div className="bg-red-50 text-red-700 p-4 rounded-lg border border-red-200">
                        {error}
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Alias */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Alias (Requerido) *</label>
                        <input
                            name="alias" required value={form.alias} onChange={handleChange}
                            placeholder="Ej. Mamá Venezuela"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0052FF] focus:border-[#0052FF] outline-none"
                        />
                        <p className="text-xs text-gray-500 mt-1">Debe ser único. Así lo buscarás en el bot.</p>
                    </div>

                    {/* Nombre Completo */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Nombre Completo *</label>
                        <input
                            name="full_name" required value={form.full_name} onChange={handleChange}
                            placeholder="Ej. Maria Perez"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0052FF] focus:border-[#0052FF] outline-none"
                        />
                    </div>

                    {/* País Destino */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">País Destino *</label>
                        <select
                            name="dest_country" required value={form.dest_country} onChange={handleChange}
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0052FF] focus:border-[#0052FF] outline-none bg-white font-medium"
                        >
                            <option value="VENEZUELA">Venezuela (Bs)</option>
                            <option value="VENEZUELA_CASH">Venezuela (Dólar Efectivo)</option>
                            <option value="COLOMBIA">Colombia (COP)</option>
                            <option value="PERU">Perú (Soles)</option>
                            <option value="CHILE">Chile (CLP)</option>
                            <option value="ARGENTINA">Argentina (ARS)</option>
                            <option value="MEXICO">México (MXN)</option>
                            <option value="USA">USA (Zelle/Cash App)</option>
                        </select>
                    </div>

                    {/* Teléfono */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Teléfono</label>
                        <input
                            name="phone" value={form.phone} onChange={handleChange}
                            placeholder="+58 412..."
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0052FF] outline-none"
                        />
                    </div>

                    {/* Banco */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Banco / Institución</label>
                        <input
                            name="bank_name" value={form.bank_name} onChange={handleChange}
                            placeholder="Ej. Banesco, Bancolombia, BCP..."
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0052FF] outline-none"
                        />
                    </div>

                    {/* Nro Cuenta */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Nro. de Cuenta / ID</label>
                        <input
                            name="account_number" value={form.account_number} onChange={handleChange}
                            placeholder="0134... / Correo Zelle"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0052FF] outline-none"
                        />
                    </div>

                    {/* Método de Pago */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Cuenta</label>
                        <input
                            name="payment_method" value={form.payment_method} onChange={handleChange}
                            placeholder="Ej. Ahorro, Corriente, Pago Móvil..."
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0052FF] outline-none"
                        />
                    </div>
                </div>

                {/* Notas */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Cédula / Notas Adicionales</label>
                    <textarea
                        name="notes" value={form.notes} onChange={handleChange} rows={3}
                        placeholder="Cédula: 12345678. Notas adicionales..."
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0052FF] outline-none resize-none"
                    ></textarea>
                </div>

                <div className="pt-4 border-t border-gray-100 flex justify-end gap-3">
                    <Link
                        href="/clientes"
                        className="px-5 py-2.5 rounded-lg font-medium text-gray-600 hover:bg-gray-100 transition-colors"
                    >
                        Cancelar
                    </Link>
                    <button
                        type="submit"
                        disabled={loading}
                        className="bg-[#0052FF] hover:bg-blue-700 text-white px-8 py-2.5 rounded-lg font-medium transition-colors disabled:opacity-50 shadow-sm"
                    >
                        {loading ? "Guardando..." : "Guardar Beneficiario"}
                    </button>
                </div>
            </form>
        </div>
    );
}
