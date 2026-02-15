const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://apii-maxx-production.up.railway.app';

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
      if (typeof window !== 'undefined') {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_role');
        localStorage.removeItem('auth_name');
        window.location.href = '/login';
      }
      throw new Error('SESSION_EXPIRED');
    }
    const errorText = await response.text().catch(() => '');
    throw new Error(errorText || 'HTTP ' + response.status);
  }

  return response.json();
}

export { API_BASE };
