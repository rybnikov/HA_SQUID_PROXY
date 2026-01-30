import { requestJson } from './client';

export interface StatusResponse {
  status: string;
  service: string;
  version: string;
  manager_initialized: boolean;
}

export async function getStatus(): Promise<StatusResponse> {
  return requestJson<StatusResponse>('/');
}
