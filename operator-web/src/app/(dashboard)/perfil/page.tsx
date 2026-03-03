"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet } from "@/lib/api";

interface Profile {
    email: string;
    alias: string;
    trust_score: number;
    kyc_status: string;
    created_at: string;
    total_orders: number;
    total_earned: number;
}

export default function PerfilPage() {
    const router = useRouter();
    const [profile, setProfile] = useState<Profile | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadProfile();
    }, []);

    const loadProfile = async () => {
        try {
            // Obtener datos del localStorage primero
            const email = localStorage.getItem("operator_email") || "";
            const alias = localStorage.getItem("operator_alias") || "";

            // Luego obtener stats del backend
            const stats = await apiGet("/api/operators/dashboard/stats");

            setProfile({
                email,
                alias,
                trust_score: stats.trust_score || 0,
                kyc_status: "APPROVED", // Ya pasó el login, está aprobado
                created_at: new Date().toISOString(), // Placeholder
                total_orders: stats.total_orders || 0,
                total_earned: stats.total_earned || 0,
            });
        } catch (err: any) {
            console.error("Error:", err);
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        localStorage.clear();
        document.cookie = "auth_token=; path=/; max-age=0";
        router.push("/login");
    };

    if (loading) {
        return (
            <div className="p-8 max-w-7xl mx-auto">
                <div className="card-glass p-6">
                    <p className="text-white">Cargando perfil...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-8 max-w-4xl mx-auto space-y-6 animate-slide-up">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold text-white mb-2">Mi Perfil</h1>
                <p className="text-white/60">Información de tu cuenta de operador</p>
            </div>

            {/* Información personal */}
            <div className="card-glass p-6 space-y-6">
                <div className="flex items-center gap-6">
                    <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-3xl font-bold">
                        {profile?.alias?.charAt(0).toUpperCase() || "?"}
                    </div>
                    <div>
                        <h2 className="text-2xl font-bold text-white">{profile?.alias}</h2>
                        <p className="text-white/60">{profile?.email}</p>
                        <div className="flex items-center gap-2 mt-2">
                            <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
                                KYC Aprobado
                            </span>
                            <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30">
                                Trust Score: {profile?.trust_score.toFixed(0)}%
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Estadísticas */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="card-glass p-6">
                    <p className="text-white/60 text-sm mb-2">Total de Órdenes</p>
                    <p className="text-3xl font-bold text-white">{profile?.total_orders}</p>
                </div>

                <div className="card-glass p-6">
                    <p className="text-white/60 text-sm mb-2">Total Ganado</p>
                    <p className="text-3xl font-bold text-green-400">
                        ${profile?.total_earned?.toFixed(2) || "0.00"}
                    </p>
                </div>
            </div>

            {/* Información de cuenta */}
            <div className="card-glass p-6">
                <h3 className="text-lg font-bold text-white mb-4">
                    Información de Cuenta
                </h3>
                <div className="space-y-4">
                    <div className="flex items-center justify-between py-3 border-b border-white/10">
                        <span className="text-white/60">Email</span>
                        <span className="text-white">{profile?.email}</span>
                    </div>
                    <div className="flex items-center justify-between py-3 border-b border-white/10">
                        <span className="text-white/60">Alias</span>
                        <span className="text-white">{profile?.alias}</span>
                    </div>
                    <div className="flex items-center justify-between py-3 border-b border-white/10">
                        <span className="text-white/60">Estado KYC</span>
                        <span className="text-green-400 font-medium">Aprobado</span>
                    </div>
                    <div className="flex items-center justify-between py-3">
                        <span className="text-white/60">Trust Score</span>
                        <span className="text-white font-medium">
                            {profile?.trust_score.toFixed(0)}%
                        </span>
                    </div>
                </div>
            </div>

            {/* Acciones */}
            <div className="card-glass p-6">
                <h3 className="text-lg font-bold text-white mb-4">Acciones</h3>
                <div className="space-y-3">
                    <button
                        onClick={handleLogout}
                        className="w-full py-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/30 font-medium rounded-xl transition-all"
                    >
                        Cerrar Sesión
                    </button>
                </div>
            </div>
        </div>
    );
}
