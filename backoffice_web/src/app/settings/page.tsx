'use client';
import React from 'react';
import { Settings, ArrowLeft } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function PlaceholderPage() {
  const router = useRouter();
  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center text-center animate-fade-in px-4">
      <div className="w-20 h-20 bg-cyan-500/10 border border-cyan-500/30 rounded-full flex items-center justify-center mb-6">
        <Settings size={40} className="text-cyan-400 animate-spin-slow" />
      </div>
      <h1 className="text-3xl font-black text-white tracking-tight mb-2">Módulo en Refactorización</h1>
      <p className="text-gray-400 max-w-md mb-8">
        Esta sección está siendo reescrita con el nuevo diseño Glassmorphism 10x y estará disponible próximamente en la Fase 4.
      </p>
      <button 
        onClick={() => router.back()}
        className="flex items-center gap-2 px-6 py-3 rounded-xl bg-white/5 border border-white/10 text-white font-bold hover:bg-white/10 transition-colors"
      >
        <ArrowLeft size={18} /> Volver Atrás
      </button>
    </div>
  );
}