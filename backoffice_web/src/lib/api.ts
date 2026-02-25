const API_BASE = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKOFFICE_API_BASE || '';

if (typeof window !== 'undefined') {
  console.log("NEXT_PUBLIC_API_URL detectada:", process.env.NEXT_PUBLIC_API_URL);
  console.log("NEXT_PUBLIC_BACKOFFICE_API_BASE detectada:", process.env.NEXT_PUBLIC_BACKOFFICE_API_BASE);
  console.log("API_BASE resultante:", API_BASE);

  if (!API_BASE) {
    console.error("CRÍTICO: API_BASE está vacía. Las peticiones al backend fallarán (404).");
  }
}

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

  if (token) {
    headers['Authorization'] = 'Bearer ' + token;
  }

  if (apiKey) {
    headers['X-API-KEY'] = apiKey;
  }

  const response = await fetch(API_BASE + endpoint, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      if (typeof window !== 'undefined' && !endpoint.includes('/auth/login')) {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_role');
        localStorage.removeItem('auth_name');
        window.location.href = '/login';
      }
      const errorText = await response.text().catch(() => '');
      throw new Error(errorText || 'UNAUTHORIZED');
    }
    const errorText = await response.text().catch(() => '');
    throw new Error(errorText || 'HTTP ' + response.status);
  }

  return response.json();
}

export async function apiGet<T>(endpoint: string): Promise<T> {
  return apiRequest<T>(endpoint, { method: 'GET' });
}

export async function apiPost<T>(endpoint: string, body: unknown): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function apiPut<T>(endpoint: string, body: unknown): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'PUT',
    body: JSON.stringify(body),
  });
}

export { API_BASE };
