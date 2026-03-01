"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
    const [operatorId, setOperatorId] = useState("");
    const router = useRouter();

    const handleLogin = (e: React.FormEvent) => {
        e.preventDefault();
        if (!operatorId.trim()) return;

        // Login rudimentario: guardamos el ID como token
        localStorage.setItem("auth_token", operatorId.trim());

        // Redirigir al dashboard
        router.push("/");
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-[#F5F7FA]">
            <div className="bg-white p-8 rounded-xl shadow-md w-full max-w-md border border-gray-100">
                <div className="text-center mb-8">
                    <h1 className="text-2xl font-bold text-[#0052FF]">Sendmax Terminal</h1>
                    <p className="text-gray-500 mt-2 text-sm">Ingreso de Operadores</p>
                </div>

                <form onSubmit={handleLogin} className="space-y-6">
                    <div>
                        <label htmlFor="operatorId" className="block text-sm font-medium text-gray-700 mb-1">
                            Operator ID (Numérico)
                        </label>
                        <input
                            id="operatorId"
                            type="number"
                            value={operatorId}
                            onChange={(e) => setOperatorId(e.target.value)}
                            className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-[#0052FF] focus:border-[#0052FF] outline-none transition-all placeholder:text-gray-400 text-gray-900"
                            placeholder="Ejemplo: 1"
                            required
                        />
                    </div>

                    <button
                        type="submit"
                        className="w-full bg-[#0052FF] hover:bg-blue-700 text-white font-medium py-3 px-4 rounded-lg transition-colors focus:ring-4 focus:ring-blue-200 outline-none"
                    >
                        Entrar al Panel
                    </button>
                </form>
            </div>
        </div>
    );
}
