import AuthGuard from "@/components/AuthGuard";
import Link from "next/link";

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <AuthGuard>
            <div className="flex flex-col min-h-screen bg-[#F5F7FA]">
                <nav className="bg-white border-b border-gray-200 px-8 py-4">
                    <div className="max-w-7xl mx-auto flex items-center justify-between">
                        <div className="flex items-center gap-8">
                            <span className="font-black text-xl tracking-tight text-[#0052FF]">SENDMAX</span>
                            <div className="hidden md:flex gap-6">
                                <Link href="/" className="text-gray-600 hover:text-[#0052FF] font-medium text-sm transition-colors">
                                    Dashboard
                                </Link>
                                <Link href="/clientes" className="text-gray-600 hover:text-[#0052FF] font-medium text-sm transition-colors">
                                    Clientes
                                </Link>
                                <Link href="/ordenes" className="text-gray-600 hover:text-[#0052FF] font-medium text-sm transition-colors">
                                    Órdenes
                                </Link>
                                <Link href="/billetera" className="text-gray-600 hover:text-[#0052FF] font-medium text-sm transition-colors">
                                    Billetera
                                </Link>
                                <Link href="/perfil" className="text-gray-600 hover:text-[#0052FF] font-medium text-sm transition-colors">
                                    Perfil
                                </Link>
                            </div>
                        </div>
                    </div>
                </nav>
                <main className="flex-1">
                    {children}
                </main>
            </div>
        </AuthGuard>
    );
}
