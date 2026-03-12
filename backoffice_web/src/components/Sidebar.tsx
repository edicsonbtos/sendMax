'use client';

import React, { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
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
import { cn } from "@/lib/utils";

const adminMenu = [
  { text: "Overview", path: "/admin", icon: BarChart, description: "Dashboard principal" },
  { text: "Órdenes", path: "/orders", icon: Receipt, description: "Gestionar órdenes" },
  { text: "Billeteras Origen", path: "/origin", icon: Wallet, description: "Entradas y sweeps" },
  { text: "Métricas", path: "/metrics", icon: LineChart, description: "Profit y volumen" },
  { text: "Cierre Diario", path: "/daily-close", icon: Calendar, description: "Reportes y cierres" },
  { text: "Usuarios", path: "/users", icon: Users, description: "Gestionar operadores" },
  { text: "Rutas Comisión", path: "/routes", icon: Receipt, description: "Márgenes por ruta" },
  { text: "Configuración", path: "/settings", icon: Settings, description: "Reglas y márgenes" },
  { text: "Métodos de Pago", path: "/payment-methods", icon: CreditCard, description: "Métodos por país" },
];

const operatorMenu = [
  { text: "Mi Dashboard", path: "/", icon: BarChart, description: "Mis métricas" },
  { text: "Mis Órdenes", path: "/orders", icon: Receipt, description: "Mis operaciones" },
  { text: "Métricas", path: "/metrics", icon: LineChart, description: "Mi rendimiento" },
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
        <ul className="space-y-1">
          {menuItems.map((item) => {
            const isActive = item.path === "/" ? pathname === "/" : pathname.startsWith(item.path);
            const Icon = item.icon;

            return (
              <li key={item.path}>
                <button
                  onClick={() => handleNav(item.path)}
                  className={cn(
                    "sidebar-item w-full flex items-center gap-3",
                    isActive ? "active" : ""
                  )}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.text}</span>
                </button>
              </li>
            );
          })}
        </ul>
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
