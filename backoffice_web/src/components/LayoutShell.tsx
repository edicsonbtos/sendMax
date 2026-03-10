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
    <div className="flex min-h-screen bg-[var(--background)]">
      {/* Mobile Header specifically just to toggle the sidebar when md:hidden */}
      <div className="md:hidden fixed top-0 left-0 w-full h-16 bg-[#0a0f1e]/90 backdrop-blur-md border-b border-[#06b6d41a] z-30 flex items-center px-4">
        <button
          onClick={() => setMobileOpen(true)}
          className="p-2 bg-[#ffffff05] border border-[#06b6d433] rounded-lg text-[#06b6d4] hover:bg-[#06b6d41a] transition-colors shadow-lg"
        >
          <Menu size={20} />
        </button>
      </div>

      <Sidebar mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />

      <main className="flex-1 w-full min-h-screen md:max-w-[calc(100vw-264px)] pb-10 custom-scrollbar overflow-x-hidden">
        <div className="w-full max-w-[1400px] mx-auto p-4 sm:p-6 md:p-8 pt-20 md:pt-8 animate-fade-in">
          {children}
        </div>
      </main>
    </div>
  );
}
