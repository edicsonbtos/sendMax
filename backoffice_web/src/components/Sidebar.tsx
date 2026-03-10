'use client';

import React, { useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import {
  BarChart,
  ReceiptSquare,
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
  { text: "Overview", path: "/", icon: BarChart, description: "Dashboard principal" },
  { text: "Órdenes", path: "/orders", icon: ReceiptSquare, description: "Gestionar órdenes" },
  { text: "Billeteras Origen", path: "/origin", icon: Wallet, description: "Entradas y sweeps" },
  { text: "Métricas", path: "/metrics", icon: LineChart, description: "Profit y volumen" },
  { text: "Cierre Diario", path: "/daily-close", icon: Calendar, description: "Reportes y cierres" },
  { text: "Usuarios", path: "/users", icon: Users, description: "Gestionar operadores" },
  { text: "Rutas Comisión", path: "/routes", icon: ReceiptSquare, description: "Márgenes por ruta" },
  { text: "Configuración", path: "/settings", icon: Settings, description: "Reglas y márgenes" },
  { text: "Métodos de Pago", path: "/payment-methods", icon: CreditCard, description: "Métodos por país" },
];

const operatorMenu = [
  { text: "Mi Dashboard", path: "/", icon: BarChart, description: "Mis métricas" },
  { text: "Mis Órdenes", path: "/orders", icon: ReceiptSquare, description: "Mis operaciones" },
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
    <div className="flex flex-col h-full bg-[#0a0f1e] border-r border-[#ffffff14] w-[264px] shrink-0">
      {/* Logo Header */}
      <div className="p-5 flex items-center justify-between border-b border-[#06b6d41a]">
        <div
          onClick={() => handleNav("/")}
          className="flex items-center gap-3 cursor-pointer transition-opacity hover:opacity-80"
        >
          <img src="/logo.png" alt="Sendmax" className="h-9 w-auto object-contain" />
          <div className="flex flex-col">
            <h2 className="font-bold text-[#06b6d4] text-[1.1rem] leading-[1.2] tracking-tight">Sendmax</h2>
            <span className="text-[#8b5cf6] text-[0.65rem] leading-none tracking-wider uppercase font-medium">Backoffice</span>
          </div>
        </div>
        <button
          onClick={() => setMobileOpen(false)}
          className="md:hidden text-[#06b6d4] hover:bg-[#06b6d41a] p-1.5 rounded-lg transition-colors"
        >
          <X size={20} />
        </button>
      </div>

      {/* Navigation Menu */}
      <div className="flex-1 overflow-y-auto px-3 py-4 custom-scrollbar">
        <ul className="space-y-1">
          {menuItems.map((item) => {
            const isActive = item.path === "/" ? pathname === "/" : pathname.startsWith(item.path);
            const Icon = item.icon;

            return (
              <li key={item.path}>
                <button
                  onClick={() => handleNav(item.path)}
                  className={cn(
                    "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 group text-left relative",
                    isActive
                      ? "bg-[#06b6d414] border border-[#06b6d433] text-[#06b6d4]"
                      : "bg-transparent border border-transparent text-gray-300 hover:bg-[#ffffff08] hover:text-white"
                  )}
                >
                  <div className={cn(
                    "min-w-6 flex items-center justify-center transition-colors",
                    isActive ? "text-[#06b6d4]" : "text-gray-500 group-hover:text-gray-300"
                  )}>
                    <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
                  </div>

                  <div className="flex flex-col">
                    <span className={cn(
                      "text-sm tracking-tight",
                      isActive ? "font-bold" : "font-medium"
                    )}>
                      {item.text}
                    </span>
                    {!isActive && (
                      <span className="text-[0.65rem] text-gray-500 mt-0.5 leading-[1.2]">
                        {item.description}
                      </span>
                    )}
                  </div>

                  {isActive && (
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 w-1 h-6 rounded bg-[#06b6d4] shadow-[0_0_8px_rgba(6,182,212,0.5)]" />
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      <div className="mx-4 border-t border-[#06b6d41a]" />

      {/* User Profile Footer */}
      <div className="p-4 pb-5">
        {token && (
          <button
            onClick={logout}
            className="w-full flex items-center justify-center gap-2 mb-4 px-4 py-2 border border-[#ef44444d] text-[#ef4444] rounded-xl text-sm font-medium hover:bg-[#ef444414] hover:border-[#ef4444] transition-colors"
          >
            <LogOut size={16} />
            Cerrar Sesión
          </button>
        )}

        <div className="flex items-center gap-3 p-2 rounded-xl bg-[#ffffff05] border border-[#ffffff0a]">
          <div className="w-9 h-9 rounded-full bg-[#06b6d426] text-[#06b6d4] flex items-center justify-center text-xs font-bold border border-[#06b6d44d]">
            {getInitials(fullName)}
          </div>
          <div className="flex flex-col">
            <span className="text-gray-200 font-semibold text-xs leading-[1.2]">
              {fullName || "Usuario"}
            </span>
            <span className="text-[#8b5cf6] text-[0.65rem] leading-[1.2] font-medium">
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
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden transition-opacity"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar Wrapper */}
      <aside className={cn(
        "fixed md:sticky top-0 left-0 h-screen z-50 transition-transform duration-300 md:translate-x-0 overflow-hidden",
        mobileOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full"
      )}>
        {SidebarContent}
      </aside>
    </>
  );
}
