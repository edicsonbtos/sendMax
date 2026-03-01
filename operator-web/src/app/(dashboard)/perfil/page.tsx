"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function PerfilPage() {
    const router = useRouter();
    const [userId, setUserId] = useState<string | null>(null);

    useEffect(() => {
        const token = localStorage.getItem("auth_token") || localStorage.getItem("operator_token");
        if (!token) {
            router.push("/login");
        } else {
            setUserId(token);
        }
    }, [router]);

    const handleLogout = () => {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("operator_token");
        router.push("/login");
    };

    return (
        <div className="p-8 max-w-3xl mx-auto">
            <h1 className="text-3xl font-black text-gray-900 tracking-tight mb-8">Mi Perfil</h1>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 mb-6">
                <div className="flex items-center justify-between mb-8 pb-8 border-b border-gray-100">
                    <div>
                        <h2 className="text-xl font-bold text-gray-800 mb-1">Información de Cuenta</h2>
                        <p className="text-gray-500 text-sm">Gestiona tus credenciales y configuración.</p>
                    </div>
                    <div className="bg-[#0052FF]/10 text-[#0052FF] font-mono px-4 py-2 rounded-lg font-bold">
                        ID: {userId || "Desconocido"}
                    </div>
                </div>

                <div className="space-y-6">
                    <div>
                        <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wider mb-4">
                            Credenciales
                        </h3>
                        <div className="opacity-60 pointer-events-none">
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-gray-700 mb-1">Correo Electrónico</label>
                                <input
                                    type="email"
                                    value="user@example.com"
                                    disabled
                                    className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-500"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Contraseña</label>
                                <input
                                    type="password"
                                    value="********"
                                    disabled
                                    className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-500"
                                />
                            </div>
                        </div>
                        <p className="text-xs font-semibold text-orange-500 mt-3 flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-orange-500"></span>
                            Cambio de credenciales en desarrollo
                        </p>
                    </div>
                </div>
            </div>

            <div className="bg-red-50 rounded-xl border border-red-100 p-6 flex items-center justify-between gap-4">
                <div>
                    <h3 className="text-red-800 font-bold mb-1">Cerrar Sesión</h3>
                    <p className="text-red-600/80 text-sm">Cierra tu sesión de forma segura en este dispositivo.</p>
                </div>
                <button
                    onClick={handleLogout}
                    className="bg-red-500 hover:bg-red-600 text-white font-semibold py-2.5 px-6 rounded-lg transition-colors shadow-sm whitespace-nowrap"
                >
                    Cerrar sesión
                </button>
            </div>
        </div>
    );
}
