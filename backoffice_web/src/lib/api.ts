const API_BASE = 'https://api-max-production.up.railway.app';

if (typeof window !== 'undefined' && API_BASE === 'http://localhost:8000' && window.location.hostname !== 'localhost') {
  console.error('[SENDMAX] NEXT_PUBLIC_BACKOFFICE_API_BASE no configurada - usando localhost como fallback');
}

export function getApiKey(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('BACKOFFICE_API_KEY');
}

export function setApiKey(key: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('BACKOFFICE_API_KEY', key);
}

export function clearApiKey(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('BACKOFFICE_API_KEY');
}

export async function apiRequest<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const apiKey = getApiKey();

  if (!apiKey) {
    throw new Error('NO_API_KEY');
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'X-API-KEY': apiKey,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      throw new Error('API_KEY_INVALID');
    }
    const errorText = await response.text();
    throw new Error(errorText || `HTTP ${response.status}`);
  }

  return response.json();
}

export { API_BASE };
