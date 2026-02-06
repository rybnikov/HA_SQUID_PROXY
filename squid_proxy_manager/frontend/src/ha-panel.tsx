import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import ReactDOM from 'react-dom/client';

import { apiFetch } from './api/client';
import { App } from './App';
import './index.css';

interface SquidPanelConfig {
  api_base?: string;
  supervisor_token?: string;
  app_basename?: string;
}

interface HAPanelLike {
  config?: SquidPanelConfig;
  url_path?: string;
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false
    }
  }
});

class SquidProxyPanel extends HTMLElement {
  private root?: ReactDOM.Root;
  private container?: HTMLDivElement;
  private panelConfig: SquidPanelConfig = {};

  public set hass(_hass: unknown) {
    window.__HASS__ = _hass;
    // Store HA's authenticated fetch for API calls through ingress
    const hassObj = _hass as { fetchWithAuth?: (url: string, init?: RequestInit) => Promise<Response> };
    if (hassObj?.fetchWithAuth) {
      window.__HASS_FETCH_WITH_AUTH__ = hassObj.fetchWithAuth.bind(hassObj);
    }
    window.dispatchEvent(new CustomEvent('ha-hass-changed', { detail: _hass }));
    this.ensureMounted();
  }

  public set panel(panel: unknown) {
    const value = panel as HAPanelLike | undefined;
    if (value?.config) {
      this.panelConfig = { ...this.panelConfig, ...value.config };
    }
    if (!this.panelConfig.app_basename && value?.url_path) {
      this.panelConfig.app_basename = `/${value.url_path}`;
    }
    this.applyRuntimeConfig();
    this.ensureMounted();
  }

  public set route(_route: unknown) {
    this.ensureMounted();
  }

  public set narrow(_narrow: boolean) {
    this.ensureMounted();
  }

  public set config(value: SquidPanelConfig) {
    this.panelConfig = value ?? {};
    this.applyRuntimeConfig();
    this.ensureMounted();
  }

  connectedCallback() {
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'squid-proxy-panel-root';
      this.appendChild(this.container);
    }
    this.applyRuntimeConfig();
    this.ensureMounted();
  }

  disconnectedCallback() {
    this.root?.unmount();
    this.root = undefined;
  }

  private applyRuntimeConfig() {
    if (this.panelConfig.api_base) {
      window.__SQUID_PROXY_API_BASE__ = this.panelConfig.api_base;
    }
    if (this.panelConfig.supervisor_token) {
      window.__SUPERVISOR_TOKEN__ = this.panelConfig.supervisor_token;
    }
    window.__APP_BASENAME__ = this.panelConfig.app_basename ?? '/squid-proxy-manager/';
    window.apiFetch = apiFetch;
  }

  private ensureMounted() {
    if (!this.container) {
      return;
    }
    if (!this.root) {
      this.root = ReactDOM.createRoot(this.container);
    }
    this.root.render(
      <React.StrictMode>
        <QueryClientProvider client={queryClient}>
          <App />
        </QueryClientProvider>
      </React.StrictMode>
    );
  }
}

customElements.define('squid-proxy-panel', SquidProxyPanel);
