"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import Link from "next/link";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";

type Beneficiary = {
    id: number;
    alias: string;
    full_name: string;
    dest_country: string;
    bank_name: string;
    account_number: string;
    phone: string;
    payment_method: string;
    notes: string;
    uses_count: number;
    created_at: string;
};

export default function ClientesPage() {
    const [beneficiaries, setBeneficiaries] = useState<Beneficiary[]>([]);
    const [filtered, setFiltered] = useState<Beneficiary[]>([]);
    const [search, setSearch] = useState("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const router = useRouter();

    useEffect(() => {
        api.get("/api/operators/beneficiaries")
            .then(res => {
                setBeneficiaries(res.data);
                setFiltered(res.data);
            })
            .catch(err => {
                if (err.response?.status === 401) {
                    setError("Tu sesión expiró");
                    localStorage.removeItem("auth_token");
                } else {
                    setError("Error cargando clientes");
                }
            })
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        const q = search.toLowerCase();
        setFiltered(beneficiaries.filter(b => b.alias.toLowerCase().includes(q) || b.full_name.toLowerCase().includes(q)));
    }, [search, beneficiaries]);

    return (
        <div className="max-w-7xl mx-auto">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold text-[#0052FF]">Agenda de Clientes</h1>
                    <p className="text-gray-500 text-sm mt-1">Beneficiarios guardados por ti</p>
                </div>
                <Link
                    href="/clientes/nuevo"
                    className="bg-[#0052FF] hover:bg-blue-700 text-white px-5 py-2.5 rounded-lg font-medium transition-colors shadow-sm"
                >
                    + Nuevo Beneficiario
                </Link>
            </div>

            {error ? (
                <div className="bg-red-50 border border-red-200 p-6 rounded-xl text-center">
                    <p className="text-red-700 font-medium mb-4">{error}</p>
                    {error === "Tu sesión expiró" && (
                        <button
                            onClick={() => router.push("/login")}
                            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                        >
                            Ir al Login
                        </button>
                    )}
                </div>
            ) : (
                <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                    <div className="p-4 border-b border-gray-100">
                        <input
                            type="text"
                            placeholder="Buscar por alias o nombre..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full md:w-1/3 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#0052FF] focus:border-[#0052FF] outline-none"
                        />
                    </div>

                    {loading ? (
                        <div className="p-12 text-center text-gray-500 animate-pulse">Cargando agenda...</div>
                    ) : filtered.length === 0 ? (
                        <div className="p-12 text-center text-gray-500">
                            No se encontraron beneficiarios.
                        </div>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="w-full text-left text-sm whitespace-nowrap">
                                <thead className="bg-gray-50 text-gray-500 font-medium">
                                    <tr>
                                        <th className="px-6 py-3">Alias</th>
                                        <th className="px-6 py-3">Nombre Completo</th>
                                        <th className="px-6 py-3">Destino</th>
                                        <th className="px-6 py-3">Banco / Cuenta</th>
                                        <th className="px-6 py-3 text-center">Envíos</th>
                                        <th className="px-6 py-3 text-right">Añadido</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-100">
                                    {filtered.map(b => (
                                        <tr key={b.id} className="hover:bg-gray-50 transition-colors">
                                            <td className="px-6 py-4 font-semibold text-gray-900">{b.alias}</td>
                                            <td className="px-6 py-4 text-gray-700">{b.full_name}</td>
                                            <td className="px-6 py-4">
                                                <span className="bg-blue-50 text-blue-700 px-2.5 py-1 rounded-md text-xs font-semibold">
                                                    {b.dest_country.replace('_', ' ')}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4">
                                                <p className="text-gray-900 font-medium">{b.bank_name || "-"}</p>
                                                <p className="text-xs text-gray-500">{b.account_number || "Sin cuenta"}</p>
                                            </td>
                                            <td className="px-6 py-4 text-center">
                                                <span className="bg-green-100 text-green-800 px-2 py-0.5 rounded-full font-bold text-xs">
                                                    {b.uses_count}
                                                </span>
                                            </td>
                                            <td className="px-6 py-4 text-right text-gray-400 text-xs">
                                                {formatDistanceToNow(new Date(b.created_at), { addSuffix: true, locale: es })}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
