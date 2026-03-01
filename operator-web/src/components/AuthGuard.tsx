"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
    const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
    const router = useRouter();

    useEffect(() => {
        const token = localStorage.getItem("auth_token");
        if (!token) {
            router.push("/login"); // Redirigir a login si no hay token
        } else {
            setIsAuthenticated(true);
        }
    }, [router]);

    // Mientras verificamos si hay token, mostramos una carga en blanco o esqueleto
    if (isAuthenticated === null) {
        return (
            <div className="min-h-screen bg-[#F5F7FA] flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0052FF]"></div>
            </div>
        );
    }

    return <>{children}</>;
}
