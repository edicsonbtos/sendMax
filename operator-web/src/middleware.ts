import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
    // Intentar obtener token de cookies o localStorage (via header en SSR)
    const token = request.cookies.get("auth_token")?.value;

    // Rutas públicas que no requieren autenticación
    const publicPaths = ["/login"];
    const isPublicPath = publicPaths.some((path) =>
        request.nextUrl.pathname.startsWith(path)
    );

    // Si no hay token y la ruta es privada, redirigir a login
    if (!token && !isPublicPath) {
        return NextResponse.redirect(new URL("/login", request.url));
    }

    // Si hay token y está en login, redirigir al dashboard
    if (token && request.nextUrl.pathname === "/login") {
        return NextResponse.redirect(new URL("/", request.url));
    }

    return NextResponse.next();
}

export const config = {
    matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
