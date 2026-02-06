import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import ReactDOM from 'react-dom/client';

import { App } from './App';

import { apiFetch } from '@/api/client';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false
    }
  }
});

window.apiFetch = apiFetch;

// When the ingress escape bootstrap is active, the panel renders in the
// parent frame with native HA web components - skip the SPA in the iframe.
if (!(window as { __HA_INGRESS_ESCAPE__?: boolean }).__HA_INGRESS_ESCAPE__) {
  ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </React.StrictMode>
  );
}
