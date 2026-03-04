import axios from 'axios';

const api = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'https://sendmax11-production.up.railway.app',
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

// ✅ FIXED: PREVENIR BUCLE INFINITO
let isRedirecting = false;

// Interceptor para manejar errores de autenticación
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response?.status === 401 && !isRedirecting) {
            isRedirecting = true;
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            localStorage.clear();
            document.cookie = "auth_token=; path=/; max-age=0";

            // Solo redirigir si NO estamos ya en login
            if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

// ✅ CRÍTICO: EXPORT DEFAULT
export default api;
