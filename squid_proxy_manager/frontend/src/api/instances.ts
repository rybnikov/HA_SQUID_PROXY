import { apiFetch, requestJson } from './client';
import { mockApiClient } from './mockData';

// Check if we're running in mock mode
const isMockMode = import.meta.env.VITE_MOCK_MODE === 'true';

export type ProxyType = 'squid' | 'tls_tunnel';

export interface ProxyInstance {
  name: string;
  proxy_type: ProxyType;
  port: number;
  https_enabled: boolean;
  status: 'running' | 'stopped' | 'initializing' | 'error';
  running?: boolean;
  user_count?: number;
  forward_address?: string;
  cover_domain?: string;
}

export interface InstancesResponse {
  instances: ProxyInstance[];
  count: number;
}

export interface CreateInstancePayload {
  name: string;
  proxy_type: ProxyType;
  port: number;
  https_enabled: boolean;
  users: { username: string; password: string }[];
  cert_params?: CertParams;
  forward_address?: string;
  cover_domain?: string;
}

export interface CertParams {
  common_name?: string | null;
  validity_days?: number;
  key_size?: number;
  country?: string;
  organization?: string;
}

export interface UserResponse {
  users: { username: string }[];
}

export interface LogsResponse {
  text: string;
}

export interface CertificateInfo {
  status: 'valid' | 'missing' | 'invalid';
  common_name?: string | null;
  not_valid_before?: string | null;
  not_valid_after?: string | null;
  pem?: string | null;
  error?: string | null;
}

export async function getInstances(): Promise<InstancesResponse> {
  if (isMockMode) {
    return mockApiClient.getInstances();
  }
  return requestJson<InstancesResponse>('api/instances');
}

export async function createInstance(payload: CreateInstancePayload) {
  if (isMockMode) {
    return mockApiClient.createInstance(payload);
  }
  return requestJson<{ status: string }>('api/instances', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function startInstance(name: string) {
  if (isMockMode) {
    return mockApiClient.startInstance(name);
  }
  return requestJson<{ status: string }>(`api/instances/${name}/start`, { method: 'POST' });
}

export async function stopInstance(name: string) {
  if (isMockMode) {
    return mockApiClient.stopInstance(name);
  }
  return requestJson<{ status: string }>(`api/instances/${name}/stop`, { method: 'POST' });
}

export async function deleteInstance(name: string) {
  if (isMockMode) {
    return mockApiClient.deleteInstance(name);
  }
  return requestJson<{ status: string }>(`api/instances/${name}`, { method: 'DELETE' });
}

export async function updateInstance(name: string, payload: Partial<CreateInstancePayload>) {
  if (isMockMode) {
    return mockApiClient.updateInstance(name, payload);
  }
  return requestJson<{ status: string }>(`api/instances/${name}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function getUsers(name: string): Promise<UserResponse> {
  if (isMockMode) {
    return mockApiClient.getUsers(name);
  }
  return requestJson<UserResponse>(`api/instances/${name}/users`);
}

export async function addUser(name: string, username: string, password: string) {
  if (isMockMode) {
    return mockApiClient.addUser(name, username);
  }
  return requestJson<{ status: string }>(`api/instances/${name}/users`, {
    method: 'POST',
    body: JSON.stringify({ username, password })
  });
}

export async function removeUser(name: string, username: string) {
  if (isMockMode) {
    return mockApiClient.removeUser(name, username);
  }
  return requestJson<{ status: string }>(`api/instances/${name}/users/${username}`, {
    method: 'DELETE'
  });
}

export async function getLogs(name: string, type: 'cache' | 'access' | 'nginx') {
  if (isMockMode) {
    return mockApiClient.getLogs(name, type);
  }
  const response = await apiFetch(`api/instances/${name}/logs?type=${type}`);
  return response.text();
}

export async function clearLogs(name: string, type: 'cache' | 'access' | 'nginx' = 'access') {
  if (isMockMode) {
    return mockApiClient.clearLogs();
  }
  return requestJson<{ status: string }>(`api/instances/${name}/logs/clear?type=${type}`, {
    method: 'POST'
  });
}

export async function getCertificateInfo(name: string): Promise<CertificateInfo> {
  if (isMockMode) {
    return mockApiClient.getCertificateInfo(name);
  }
  const response = await apiFetch(`api/instances/${name}/certs`);
  if (response.status === 404) {
    return { status: 'missing' };
  }
  if (!response.ok) {
    throw await response.text();
  }
  return response.json() as Promise<CertificateInfo>;
}

export async function testConnectivity(
  name: string,
  username: string,
  password: string,
  target_url?: string
) {
  if (isMockMode) {
    return mockApiClient.testConnectivity();
  }
  return requestJson<{ status: string; message?: string }>(`api/instances/${name}/test`, {
    method: 'POST',
    body: JSON.stringify({ username, password, target_url })
  });
}

export async function regenerateCertificates(name: string) {
  if (isMockMode) {
    return mockApiClient.regenerateCertificates(name);
  }
  return requestJson<{ status: string }>(`api/instances/${name}/certs`, { method: 'POST' });
}

export async function getOvpnSnippet(name: string): Promise<string> {
  if (isMockMode) {
    return mockApiClient.getOvpnSnippet(name);
  }
  const response = await apiFetch(`api/instances/${name}/ovpn-snippet`);
  return response.text();
}
