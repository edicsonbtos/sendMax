'use client';

import React, { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { cn } from "@/lib/cn";
import {
  BarChart,
  Receipt,
  Wallet,
  Settings,
  LineChart,
  Calendar,
  Users,
  CreditCard,
  LogOut,
  Menu,
  X
} from "lucide-react";

const adminMenu = [
  { 
    category: "Control Ejecutivo",
    items: [
      { text: "Control Center", path: "/control-center", icon: BarChart, description: "Dashboard estratégico" },
      { text: "Riesgo Operativo", path: "/risk", icon: LineChart, description: "Monitor de anomalías" },
      { text: "Auditoría Log", path: "/audit", icon: Receipt, description: "Feed de eventos" },
    ]
  },
  {
    category: "Operación",
    items: [
      { text: "Órdenes", path: "/orders", icon: Receipt, description: "Gestión de remesas" },
      { text: "Usuarios", path: "/users", icon: Users, description: "Operadores y perfiles" },
      { text: "Métodos de Pago", path: "/payment-methods", icon: CreditCard, description: "Configuración local" },
    ]
  },
  {
    category: "Tesorería",
    items: [
      { text: "Billeteras Origen", path: "/origin", icon: Wallet, description: "Entradas y sweeps" },
      { text: "Tesorería Central", path: "/treasury", icon: Wallet, description: "Balances corporativos" },
      { text: "Bóvedas / Vaults", path: "/vaults", icon: Wallet, description: "Radar de liquidez" },
    ]
  },
  {
    category: "Configuración",
    items: [
      { text: "Métricas", path: "/metrics", icon: LineChart, description: "KPIs históricos" },
      { text: "Cierre Diario", path: "/daily-close", icon: Calendar, description: "Snapshots legales" },
      { text: "Rutas Comisión", path: "/routes", icon: Receipt, description: "Márgenes" },
      { text: "Ajustes", path: "/settings", icon: Settings, description: "Sistema" },
      { text: "Overview Original", path: "/admin", icon: BarChart, description: "Admin legacy" },
    ]
  }
];

const operatorMenu = [
  { 
    category: "Mi Operativa",
    items: [
      { text: "Escritorio", path: "/", icon: BarChart, description: "Mis números" },
      { text: "Tablero Órdenes", path: "/orders", icon: Receipt, description: "Operaciones" },
      { text: "Mis Métricas", path: "/metrics", icon: LineChart, description: "Rendimiento" },
    ]
  }
];

export default function Sidebar({ mobileOpen, setMobileOpen }: { mobileOpen: boolean, setMobileOpen: (open: boolean) => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const { logout, fullName, role, token } = useAuth();

  const menuItems = (role === "admin" || role === "superadmin") ? adminMenu : operatorMenu;

  const handleNav = (path: string) => {
    router.push(path);
    setMobileOpen(false);
  };

  const getInitials = (name: string | null) => {
    if (!name) return "SM";
    return name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
  };

  const SidebarContent = (
    <div className="flex flex-col h-full sidebar w-64 flex-col shrink-0">
      {/* Logo Header */}
      <div className="p-6 border-b border-white/10">
        <div
          onClick={() => handleNav("/")}
          className="flex items-center gap-3 cursor-pointer transition-transform hover:scale-[1.02]"
        >
          <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-cyan-500 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
            <BarChart className="text-white w-6 h-6" />
          </div>
          <div className="flex flex-col">
            <h2 className="font-bold text-white text-lg leading-tight tracking-tight">SendMax</h2>
            <span className="text-blue-400 text-[10px] uppercase tracking-widest font-bold opacity-80">Backoffice</span>
          </div>
        </div>
        <button
          onClick={() => setMobileOpen(false)}
          className="lg:hidden text-white/60 hover:text-white p-1.5 rounded-lg transition-colors"
        >
          <X size={20} />
        </button>
      </div>

      {/* Navigation Menu */}
      <div className="flex-1 overflow-y-auto py-6 custom-scrollbar">
        <nav className="px-3 space-y-8">
          {menuItems.map((group) => (
            <div key={group.category} className="space-y-2">
              <h3 className="px-4 text-[10px] font-black text-white/20 uppercase tracking-[0.2em]">
                {group.category}
              </h3>
              <ul className="space-y-1">
                {group.items.map((item) => {
                  const isActive = item.path === "/" ? pathname === "/" : pathname.startsWith(item.path);
                  const Icon = item.icon;

                  return (
                    <li key={item.path}>
                      <button
                        onClick={() => handleNav(item.path)}
                        className={cn(
                          "sidebar-item w-full flex items-center gap-3 py-2 px-4 rounded-xl text-sm font-semibold transition-all duration-200",
                          isActive 
                            ? "bg-blue-600/10 text-blue-400 border border-blue-500/20 shadow-[0_0_20px_rgba(59,130,246,0.1)]" 
                            : "text-white/40 hover:text-white hover:bg-white/5 border border-transparent"
                        )}
                      >
                        <div className={cn(
                          "flex items-center justify-center w-8 h-8 rounded-lg transition-colors",
                          isActive ? "bg-blue-500/20 text-blue-400" : "text-white/20 group-hover:text-white/40"
                        )}>
                          <Icon className="w-5 h-5" />
                        </div>
                        <span>{item.text}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
      </div>

      {/* User Profile Footer */}
      <div className="p-4 border-t border-white/10">
        {token && (
          <button
            onClick={logout}
            className="sidebar-item w-full text-red-400 hover:bg-red-500/10 mb-4"
          >
            <LogOut size={16} />
            <span>Cerrar Sesión</span>
          </button>
        )}

        <div className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10">
          <div className="w-9 h-9 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs font-bold border border-blue-500/30">
            {getInitials(fullName)}
          </div>
          <div className="flex flex-col">
            <span className="text-white font-medium text-xs">
              {fullName || "Usuario"}
            </span>
            <span className="text-gray-500 text-[10px] font-medium uppercase tracking-wider">
              {role === "admin" ? "Administrador" : "Operador"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );


  return (
    <>
      {/* Mobile Backdrop */}
      <div
        className={cn(
          "fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden transition-opacity duration-300",
          mobileOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={() => setMobileOpen(false)}
      />

      {/* Sidebar Desktop */}
      <aside className="fixed top-0 left-0 z-50 h-screen transition-transform -translate-x-full lg:translate-x-0 lg:static">
        {SidebarContent}
      </aside>

      {/* Sidebar Mobile */}
      <aside
        className={cn(
          "fixed top-0 left-0 z-50 w-64 h-screen transition-transform duration-300 lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {SidebarContent}
      </aside>
    </>
  );
}
