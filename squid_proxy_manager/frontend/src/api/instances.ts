import { apiFetch, requestJson } from './client';

export interface ProxyInstance {
  name: string;
  port: number;
  https_enabled: boolean;
  status: 'running' | 'stopped' | 'initializing' | 'error';
  running?: boolean;
}

export interface InstancesResponse {
  instances: ProxyInstance[];
  count: number;
}

export interface CreateInstancePayload {
  name: string;
  port: number;
  https_enabled: boolean;
  users: { username: string; password: string }[];
  cert_params?: CertParams;
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

export async function getInstances(): Promise<InstancesResponse> {
  return requestJson<InstancesResponse>('api/instances');
}

export async function createInstance(payload: CreateInstancePayload) {
  return requestJson<{ status: string }>('api/instances', {
    method: 'POST',
    body: JSON.stringify(payload)
  });
}

export async function startInstance(name: string) {
  return requestJson<{ status: string }>(`api/instances/${name}/start`, { method: 'POST' });
}

export async function stopInstance(name: string) {
  return requestJson<{ status: string }>(`api/instances/${name}/stop`, { method: 'POST' });
}

export async function deleteInstance(name: string) {
  return requestJson<{ status: string }>(`api/instances/${name}`, { method: 'DELETE' });
}

export async function updateInstance(name: string, payload: Partial<CreateInstancePayload>) {
  return requestJson<{ status: string }>(`api/instances/${name}`, {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });
}

export async function getUsers(name: string): Promise<UserResponse> {
  return requestJson<UserResponse>(`api/instances/${name}/users`);
}

export async function addUser(name: string, username: string, password: string) {
  return requestJson<{ status: string }>(`api/instances/${name}/users`, {
    method: 'POST',
    body: JSON.stringify({ username, password })
  });
}

export async function removeUser(name: string, username: string) {
  return requestJson<{ status: string }>(`api/instances/${name}/users/${username}`, {
    method: 'DELETE'
  });
}

export async function getLogs(name: string, type: 'cache' | 'access') {
  const response = await apiFetch(`api/instances/${name}/logs?type=${type}`);
  return response.text();
}

export async function testConnectivity(name: string, username: string, password: string) {
  return requestJson<{ status: string; message?: string }>(`api/instances/${name}/test`, {
    method: 'POST',
    body: JSON.stringify({ username, password })
  });
}

export async function regenerateCertificates(name: string) {
  return requestJson<{ status: string }>(`api/instances/${name}/certs`, { method: 'POST' });
}
