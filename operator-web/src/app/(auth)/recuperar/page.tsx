"use client";
import { useState, FormEvent } from "react";
import Link from "next/link";

export default function RecuperarPage() {
    const [step, setStep] = useState<"email" | "code">("email");
    const [email, setEmail] = useState("");
    const [code, setCode] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    const handleRequestCode = async (e: FormEvent) => {
        e.preventDefault();
        setError("");
        setSuccess("");
        setLoading(true);

        try {
            const res = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/auth/operator/request-reset`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email }),
                }
            );

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || "Error enviando código");
            }

            setSuccess(data.message || "Código enviado a tu Telegram");
            setStep("code");
        } catch (err: unknown) {
            if (err instanceof Error) setError(err.message);
            else setError("Error desconocido");
        } finally {
            setLoading(false);
        }
    };

    const handleResetPassword = async (e: FormEvent) => {
        e.preventDefault();
        setError("");
        setSuccess("");
        setLoading(true);

        try {
            const res = await fetch(
                `${process.env.NEXT_PUBLIC_API_URL}/auth/operator/reset-password`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email, code, new_password: newPassword }),
                }
            );

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || "Error cambiando contraseña");
            }

            setSuccess("✅ Contraseña cambiada. Redirigiendo al login...");
            setTimeout(() => {
                window.location.href = "/login";
            }, 2000);
        } catch (err: unknown) {
            if (err instanceof Error) setError(err.message);
            else setError("Error desconocido");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
            <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-xl shadow-2xl">
                <div>
                    <h2 className="text-3xl font-bold text-center text-gray-900">
                        Recuperar Contraseña
                    </h2>
                    <p className="mt-2 text-center text-gray-600">
                        {step === "email"
                            ? "Ingresa tu email y te enviaremos un código a Telegram"
                            : "Ingresa el código que recibiste en Telegram"}
                    </p>
                </div>

                {error && (
                    <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                        {error}
                    </div>
                )}

                {success && (
                    <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
                        {success}
                    </div>
                )}

                {step === "email" ? (
                    <form onSubmit={handleRequestCode} className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Email
                            </label>
                            <input
                                type="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                placeholder="tu@email.com"
                                disabled={loading}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {loading ? "Enviando..." : "Enviar Código a Telegram"}
                        </button>

                        <div className="text-center">
                            <Link href="/login" className="text-sm text-blue-600 hover:text-blue-500">
                                ← Volver al Login
                            </Link>
                        </div>
                    </form>
                ) : (
                    <form onSubmit={handleResetPassword} className="space-y-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Código de 6 dígitos
                            </label>
                            <input
                                type="text"
                                required
                                value={code}
                                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-center text-2xl tracking-[0.5em] font-mono"
                                placeholder="000000"
                                maxLength={6}
                                disabled={loading}
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Nueva Contraseña
                            </label>
                            <input
                                type="password"
                                required
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                placeholder="Mínimo 8 caracteres"
                                minLength={8}
                                disabled={loading}
                            />
                        </div>

                        <button
                            type="submit"
                            disabled={loading || code.length < 6}
                            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        >
                            {loading ? "Cambiando..." : "Cambiar Contraseña"}
                        </button>

                        <div className="flex justify-between text-sm">
                            <button
                                type="button"
                                onClick={() => { setStep("email"); setError(""); setSuccess(""); }}
                                className="text-blue-600 hover:text-blue-500"
                            >
                                ← Reenviar código
                            </button>
                            <Link href="/login" className="text-gray-500 hover:text-gray-400">
                                Volver al Login
                            </Link>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}
