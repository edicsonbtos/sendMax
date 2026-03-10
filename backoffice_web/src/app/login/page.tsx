'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { useAuth } from '@/components/AuthProvider';
import { Mail, Lock, AlertCircle, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import Image from 'next/image';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await api.post<{
        access_token: string;
        role: string;
        full_name: string;
      }>('/auth/login', { email, password });

      const data = res.data;
      login(data.access_token, data.role, data.full_name);

      if (data.role === 'admin' || data.role === 'superadmin') {
        router.push('/');
      } else {
        router.push('/operator-office');
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 sm:p-8 animate-fade-in relative overflow-hidden bg-[#0A0F1E]">

      {/* Background Gradients */}
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent" />
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-cyan-500/20 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-purple-500/20 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute inset-0 bg-[url('/noise.png')] opacity-[0.03] mix-blend-overlay pointer-events-none"></div>

      <div className="w-full max-w-[440px] z-10">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center p-3 rounded-2xl bg-[#ffffff05] border border-[#ffffff1a] mb-4 shadow-[0_0_30px_rgba(6,182,212,0.15)]">
            <Image src="/logo.png" alt="Sendmax Logo" width={48} height={48} className="w-12 h-12 object-contain" />
          </div>
          <h1 className="text-3xl font-black text-white tracking-tight mb-2">Backoffice</h1>
          <p className="text-sm text-gray-400 font-medium">Panel de Administración de Sendmax</p>
        </div>

        <div className="card-glass p-6 sm:p-8 space-y-6">
          <div className="text-center">
            <h2 className="text-xl font-bold text-white">Iniciar Sesión</h2>
            <p className="text-sm text-gray-500 mt-1">Ingresa tus credenciales para acceder</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-sm font-medium flex items-center gap-2 animate-shake">
                <AlertCircle size={16} className="shrink-0" />
                <p>{error}</p>
              </div>
            )}

            <div className="space-y-3">
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-500 group-focus-within:text-cyan-400 transition-colors">
                  <Mail size={18} />
                </div>
                <input
                  type="email"
                  required
                  placeholder="Correo electrónico"
                  className="input-glass pl-10 w-full"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  autoFocus
                />
              </div>

              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-500 group-focus-within:text-cyan-400 transition-colors">
                  <Lock size={18} />
                </div>
                <input
                  type="password"
                  required
                  placeholder="Contraseña"
                  className="input-glass pl-10 w-full"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !email || !password}
              className="w-full relative overflow-hidden group flex items-center justify-center gap-2 py-3 px-4 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold rounded-xl transition-all shadow-[0_0_20px_rgba(6,182,212,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform" />
              <span className="relative flex items-center gap-2">
                {loading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <>
                    Ingresar <ArrowRight size={18} />
                  </>
                )}
              </span>
            </button>
          </form>
        </div>

        <div className="text-center mt-8 text-[11px] text-gray-500 font-medium">
          <p>© {new Date().getFullYear()} Sendmax Global. Todos los derechos reservados.</p>
        </div>
      </div>
    </div>
  );
}
