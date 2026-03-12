'use client';

import React, { useState } from 'react';
import { usePathname } from 'next/navigation';
import Sidebar from '@/components/Sidebar';
import { Menu } from 'lucide-react';

export default function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const isLoginPage = pathname === '/login';

  if (isLoginPage) return <>{children}</>;

  return (
    <div className="flex min-h-screen bg-primary-900">
      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 w-full h-16 bg-primary-800/95 backdrop-blur-lg border-b border-white/10 z-40 flex items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-cyan-400 rounded-lg flex items-center justify-center shadow-lg" />
          <span className="font-bold text-white tracking-tight">SendMax Admin</span>
        </div>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 bg-white/5 border border-white/10 rounded-lg text-white hover:bg-white/10 transition-all"
        >
          <Menu size={20} />
        </button>
      </div>

      <Sidebar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />

      <main className="flex-1 w-full min-h-screen lg:ml-64 pt-16 lg:pt-0 overflow-x-hidden">
        <div className="w-full max-w-[1600px] mx-auto p-4 sm:p-6 lg:p-10 animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );

}
