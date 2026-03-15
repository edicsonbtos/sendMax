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

      // Simple redirect based on role
      if (data.role === 'admin' || data.role === 'superadmin' || data.role === 'ADMIN') {
        router.replace('/control-center'); // Use replace to avoid back-nav to login
      } else {
        router.replace('/operator-office');
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

      <div className="w-full max-w-[440px] z-10">
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center p-3 rounded-2xl bg-[#ffffff05] border border-[#ffffff1a] mb-5 shadow-[0_0_30px_rgba(6,182,212,0.2)] transition-transform hover:scale-105">
            <Image src="/logo.png" alt="Sendmax Logo" width={56} height={56} className="w-14 h-14 object-contain" />
          </div>
          <h1 className="text-4xl font-black text-white tracking-tighter mb-2 bg-gradient-to-r from-white via-white to-white/40 bg-clip-text">
            Backoffice <span className="text-cyan-400">10x</span>
          </h1>
          <p className="text-sm text-gray-400 font-semibold uppercase tracking-[0.2em] opacity-80">Sendmax Global Admin</p>
        </div>

        <div className="card-glass p-8 sm:p-10 space-y-8 shadow-[0_20px_50px_rgba(0,0,0,0.3)] border-white/10">
          <div className="text-center">
            <h2 className="text-2xl font-black text-white tracking-tight">Acceso Seguro</h2>
            <p className="text-xs text-gray-500 mt-2 font-bold uppercase tracking-widest">Credenciales del Sistema</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {error && (
              <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-bold flex items-center gap-3 animate-shake">
                <AlertCircle size={18} className="shrink-0" />
                <p>{error}</p>
              </div>
            )}

            <div className="space-y-5">
              <div className="relative group">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-cyan-400 transition-colors z-10">
                  <Mail size={20} strokeWidth={2.5} />
                </div>
                <input
                  type="email"
                  required
                  placeholder="Correo electrónico"
                  className="input-glass pl-12 w-full py-4 text-sm font-medium transition-all group-focus-within:bg-white/5"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  autoFocus
                />
              </div>

              <div className="relative group">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-cyan-400 transition-colors z-10">
                  <Lock size={20} strokeWidth={2.5} />
                </div>
                <input
                  type="password"
                  required
                  placeholder="Contraseña"
                  className="input-glass pl-12 w-full py-4 text-sm font-medium transition-all group-focus-within:bg-white/5"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !email || !password}
              className="w-full relative overflow-hidden group flex items-center justify-center gap-3 py-4 bg-gradient-to-r from-cyan-600 to-purple-700 hover:from-cyan-500 hover:to-purple-600 text-white font-black text-xs uppercase tracking-[0.2em] rounded-xl transition-all shadow-[0_10px_30px_rgba(6,182,212,0.3)] active:scale-[0.98] disabled:opacity-50"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  Entrar <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>
        </div>

        <div className="text-center mt-12 text-[10px] text-gray-600 font-bold uppercase tracking-[0.3em]">
          <p>© {new Date().getFullYear()} Sendmax Global • Retroceso Seguro v1.2</p>
        </div>
      </div>
    </div>
  );
}
