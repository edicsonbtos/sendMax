import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
    const token = request.cookies.get("auth_token")?.value;
    const { pathname } = request.nextUrl;

    // Rutas públicas que NO requieren autenticación
    const publicPaths = ["/login", "/recuperar"];
    const isPublicPath = publicPaths.some(path => pathname.startsWith(path));

    // Si NO hay token y la ruta NO es pública → redirigir a login
    if (!token && !isPublicPath) {
        const loginUrl = new URL("/login", request.url);
        return NextResponse.redirect(loginUrl);
    }

    // Si hay token y está intentando acceder a login → redirigir a dashboard
    if (token && pathname === "/login") {
        const dashboardUrl = new URL("/", request.url);
        return NextResponse.redirect(dashboardUrl);
    }

    // Permitir acceso
    return NextResponse.next();
}

export const config = {
    matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
