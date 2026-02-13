import { getApiBasePath, getIngressBasename } from '@/app/ingress';

export interface ApiError {
  message: string;
  status: number;
}

declare global {
  interface Window {
    __SUPERVISOR_TOKEN__?: string;
    __APP_VERSION__?: string;
    __SQUID_PROXY_API_BASE__?: string;
    __APP_BASENAME__?: string;
    __HASS__?: unknown;
    __HASS_FETCH_WITH_AUTH__?: (url: string, init?: RequestInit) => Promise<Response>;
    apiFetch?: typeof apiFetch;
  }
}

function getToken(): string {
  const tokenValue = window.__SUPERVISOR_TOKEN__;
  if (!tokenValue) {
    return '';
  }
  if (tokenValue === '__SUPERVISOR_TOKEN__' || tokenValue === '__SUPERVISOR_TOKEN_VALUE__') {
    return '';
  }
  return tokenValue;
}

function resolvePath(path: string): string {
  if (path.startsWith('http')) {
    return path;
  }

  const explicitApiBase = window.__SQUID_PROXY_API_BASE__?.replace(/\/$/, '');
  if (explicitApiBase) {
    const sanitized = path.replace(/^\//, '');
    if (sanitized.startsWith('api/')) {
      return `${explicitApiBase}/${sanitized.slice(4)}`;
    }
    return `${explicitApiBase}/${sanitized}`;
  }

  if (path === '' || path === '/') {
    return getIngressBasename();
  }

  const sanitized = path.replace(/^\//, '');
  const apiBase = getApiBasePath();

  if (sanitized.startsWith('api/')) {
    return `${apiBase}/${sanitized.slice(4)}`;
  }

  return `${apiBase}/${sanitized}`;
}

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const url = resolvePath(path);
  const headers = new Headers(options.headers || {});
  headers.set('Content-Type', 'application/json');

  // When running as a panel in HA's main frame, use HA's authenticated fetch
  // which sends the user's auth token through the ingress proxy.
  // Only use hassFetch for relative URLs — it prepends the HA origin, so passing
  // an absolute URL (e.g. http://localhost:8099/api/…) would create an invalid
  // double-origin URL like http://localhost:8123http://localhost:8099/api/….
  const hassFetch = window.__HASS_FETCH_WITH_AUTH__;
  if (hassFetch && !url.startsWith('http')) {
    return hassFetch(url, { ...options, headers });
  }

  // Standalone / ingress iframe mode: use supervisor token directly
  const token = getToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  return fetch(url, { ...options, headers });
}

export async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await apiFetch(path, options);
  if (!response.ok) {
    let message = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errorData = await response.json();
      // Extract error message from backend response formats:
      // {"error": "message"} or {"message": "message"} or {"detail": "message"}
      message = errorData.error || errorData.message || errorData.detail || message;
    } catch {
      // If JSON parsing fails, try to get text
      try {
        const text = await response.text();
        if (text) message = text;
      } catch {
        // Keep default message
      }
    }
    throw { message, status: response.status } as ApiError;
  }
  return response.json() as Promise<T>;
}
