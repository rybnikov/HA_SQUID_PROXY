import { requestJson } from './client';

const isMockMode = import.meta.env.VITE_MOCK_MODE === 'true';

export interface StatusResponse {
  status: string;
  service: string;
  version: string;
  manager_initialized: boolean;
}

export async function getStatus(): Promise<StatusResponse> {
  if (isMockMode) {
    return {
      status: 'ok',
      service: 'squid_proxy_manager',
      version: '1.4.7-mock',
      manager_initialized: true
    };
  }
  return requestJson<StatusResponse>('/');
}
