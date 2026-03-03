const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://sendmax11-production.up.railway.app";

/**
 * Realiza una petición GET autenticada
 */
export async function apiGet(endpoint: string) {
    const token = localStorage.getItem("auth_token");

    const res = await fetch(`${API_URL}${endpoint}`, {
        headers: {
            Authorization: token ? `Bearer ${token}` : "",
        },
    });

    // Si el token expiró o es inválido, redirigir a login
    if (res.status === 401) {
        localStorage.clear();
        window.location.href = "/login";
        throw new Error("Sesión expirada");
    }

    if (!res.ok) {
        throw new Error(`Error ${res.status}: ${res.statusText}`);
    }

    return res.json();
}

/**
 * Realiza una petición POST autenticada
 */
export async function apiPost(endpoint: string, data: any) {
    const token = localStorage.getItem("auth_token");

    const res = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: token ? `Bearer ${token}` : "",
        },
        body: JSON.stringify(data),
    });

    if (res.status === 401) {
        localStorage.clear();
        window.location.href = "/login";
        throw new Error("Sesión expirada");
    }

    if (!res.ok) {
        throw new Error(`Error ${res.status}: ${res.statusText}`);
    }

    return res.json();
}

const api = {
    get: apiGet,
    post: apiPost
};

export default api;
