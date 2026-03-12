import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
  withCredentials: true,
});

let isRedirecting = false;

// Request Interceptor: Inject API Key if present
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const apiKey = localStorage.getItem('api_key');
      if (apiKey && config.headers) {
        config.headers['X-API-KEY'] = apiKey;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Handle errors
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && !isRedirecting) {
      isRedirecting = true;
      if (typeof window !== 'undefined') {
        localStorage.removeItem('admin_token');
        localStorage.removeItem('token');
        localStorage.removeItem('admin_user');
        window.location.href = '/login';
      }
      setTimeout(() => { isRedirecting = false; }, 3000);
    }
    return Promise.reject(error);
  }
);

export default api;

// Helper exports
export const apiGet = <T = any>(url: string, config = {}) =>
  api.get<T>(url, config);

export const apiPost = <T = any>(url: string, data?: any, config = {}) =>
  api.post<T>(url, data, config);

export const apiPut = <T = any>(url: string, data?: any, config = {}) =>
  api.put<T>(url, data, config);

export const apiDelete = <T = any>(url: string, config = {}) =>
  api.delete<T>(url, config);

export const apiPatch = <T = any>(url: string, data?: any, config = {}) =>
  api.patch<T>(url, data, config);

/**
 * Legacy/Compatible helper that returns data directly.
 * Matches original functional logic of restored pages.
 */
export async function apiRequest<T = any>(url: string, options: any = {}): Promise<T> {
  const method = (options.method || 'GET').toLowerCase();
  const config = {
    ...options,
    method,
  };
  
  // If options.body exists (from fetch-style calls), move to config.data for axios
  if (options.body && !config.data) {
    config.data = typeof options.body === 'string' ? JSON.parse(options.body) : options.body;
  }

  const response = await api.request<T>({
    url,
    ...config,
  });
  
  return response.data;
}
