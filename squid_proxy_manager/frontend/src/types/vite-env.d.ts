/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MOCK_MODE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

interface Window {
  __SUPERVISOR_TOKEN__?: string;
  __APP_VERSION__?: string;
  apiFetch?: (path: string, options?: RequestInit) => Promise<Response>;
}
