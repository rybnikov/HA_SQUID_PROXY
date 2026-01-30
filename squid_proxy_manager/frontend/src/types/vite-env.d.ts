/// <reference types="vite/client" />

interface Window {
  __SUPERVISOR_TOKEN__?: string;
  __APP_VERSION__?: string;
  apiFetch?: (path: string, options?: RequestInit) => Promise<Response>;
}
