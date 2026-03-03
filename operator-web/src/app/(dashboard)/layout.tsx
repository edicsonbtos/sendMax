'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import {
    LayoutDashboard,
    Users,
    FileText,
    Wallet,
    User,
    Trophy,
    TrendingUp,
    LogOut,
    Menu,
    X
} from 'lucide-react';
import { useState, useEffect } from 'react';

const menuItems = [
    { href: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { href: '/clientes', icon: Users, label: 'Contactos' },
    { href: '/ordenes', icon: FileText, label: 'Mis Órdenes' },
    { href: '/billetera', icon: Wallet, label: 'Billetera' },
    { href: '/ranking', icon: Trophy, label: 'Ranking' },
    { href: '/perfil', icon: User, label: 'Mi Perfil' },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem('token');

        if (!token && pathname !== '/login') {
            window.location.href = '/login';
        } else {
            setIsAuthenticated(true);
        }

        setIsLoading(false);
    }, [pathname, router]);

    const handleLogout = () => {
        // Limpiar todo del localStorage
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.removeItem('operatorData');
        localStorage.clear();
        document.cookie = "auth_token=; path=/; max-age=0";
        // Redirigir al login
        window.location.href = '/login';
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-black">
                <div className="text-center">
                    <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                </div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return null;
    }

    return (
        <div className="min-h-screen flex">
            {/* Sidebar Desktop */}
            <aside className="hidden lg:flex sidebar w-64 flex-col fixed h-full z-40">
                {/* Logo */}
                <div className="p-6 border-b border-white/10">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-400 rounded-xl flex items-center justify-center">
                            <TrendingUp className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-white">SendMax</h1>
                            <p className="text-xs text-gray-400">Panel de Operador</p>
                        </div>
                    </div>
                </div>

                {/* Menu */}
                <nav className="flex-1 py-6">
                    {menuItems.map((item) => (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`sidebar-item ${pathname === item.href ? 'active' : ''}`}
                        >
                            <item.icon className="w-5 h-5" />
                            <span>{item.label}</span>
                        </Link>
                    ))}
                </nav>

                {/* Footer */}
                <div className="p-4 border-t border-white/10">
                    <button onClick={handleLogout} className="sidebar-item w-full text-red-400 hover:bg-red-500/10">
                        <LogOut className="w-5 h-5" />
                        <span>Cerrar Sesión</span>
                    </button>
                </div>
            </aside>

            {/* Mobile Header */}
            <div className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-primary-800/95 backdrop-blur-lg border-b border-white/10 px-4 py-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-cyan-400 rounded-lg flex items-center justify-center">
                            <TrendingUp className="w-5 h-5 text-white" />
                        </div>
                        <span className="font-bold text-white">SendMax</span>
                    </div>
                    <button
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                        className="p-2 hover:bg-white/10 rounded-lg"
                    >
                        {sidebarOpen ? <X className="w-6 h-6 text-white" /> : <Menu className="w-6 h-6 text-white" />}
                    </button>
                </div>
            </div>

            {/* Mobile Sidebar */}
            {sidebarOpen && (
                <div className="lg:hidden fixed inset-0 z-40 bg-black/50" onClick={() => setSidebarOpen(false)}>
                    <aside className="sidebar w-64 h-full" onClick={(e) => e.stopPropagation()}>
                        <div className="pt-16">
                            <nav className="py-6">
                                {menuItems.map((item) => (
                                    <Link
                                        key={item.href}
                                        href={item.href}
                                        onClick={() => setSidebarOpen(false)}
                                        className={`sidebar-item ${pathname === item.href ? 'active' : ''}`}
                                    >
                                        <item.icon className="w-5 h-5" />
                                        <span>{item.label}</span>
                                    </Link>
                                ))}
                            </nav>
                        </div>
                    </aside>
                </div>
            )}

            {/* Main Content */}
            <main className="flex-1 lg:ml-64 pt-16 lg:pt-0 min-h-screen">
                {children}
            </main>
        </div>
    );
}
