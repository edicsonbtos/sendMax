import axios from 'axios';

const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Interceptor para agregar token automáticamente
api.interceptors.request.use(
    (config) => {
        if (typeof window !== 'undefined') {
            const token = localStorage.getItem('token');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// ✅ PREVENIR BUCLE INFINITO - Control de redirección
let isRedirecting = false;

api.interceptors.response.use(
    (response) => response,
    (error) => {
        // Manejar error 401 (No autorizado) UNA SOLA VEZ
        if (error.response?.status === 401 && !isRedirecting) {
            isRedirecting = true;

            // Limpiar autenticación
            localStorage.clear();
            document.cookie = "auth_token=; path=/; max-age=0";

            // Solo redirigir si NO estamos en rutas públicas
            if (typeof window !== 'undefined') {
                const pathname = window.location.pathname;
                const isPublicRoute = pathname.includes('/login') || pathname.includes('/recuperar');

                if (!isPublicRoute) {
                    // Usar replace para no generar entrada en historial
                    window.location.replace('/login');
                }
            }

            // Resetear flag después de 2 segundos
            setTimeout(() => {
                isRedirecting = false;
            }, 2000);
        }
        return Promise.reject(error);
    }
);

// ✅ CRÍTICO: EXPORT DEFAULT
export default api;
