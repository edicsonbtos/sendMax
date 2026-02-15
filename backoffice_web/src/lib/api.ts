const API_BASE = 'https://api-max-production.up.railway.app';

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('auth_token');
}

export function getApiKey(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('BACKOFFICE_API_KEY');
}

export async function apiRequest<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const apiKey = getApiKey();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  // JWT (nuevo)
  if (token) {
    headers['Authorization'] = 'Bearer ' + token;
  }

  // API KEY (legacy, para endpoints actuales)
  if (apiKey) {
    headers['X-API-KEY'] = apiKey;
  }

  const response = await fetch(API_BASE + endpoint, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const txt = await response.text().catch(() => '');
    // Propaga detalle si viene JSON con {"detail": "..."}
    throw new Error(txt || ('HTTP ' + response.status));
  }

  return response.json();
}

export { API_BASE };
