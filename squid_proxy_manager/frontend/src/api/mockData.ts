/**
 * Mock data for frontend development without backend
 * Used when VITE_MOCK_MODE=true
 */

import type { CertificateInfo, InstancesResponse, ProxyInstance, UserResponse } from './instances';

export const MOCK_INSTANCES: ProxyInstance[] = [
  {
    name: 'production-proxy',
    port: 3128,
    https_enabled: true,
    dpi_prevention: true,
    status: 'running',
    running: true,
    user_count: 3
  },
  {
    name: 'development-proxy',
    port: 3129,
    https_enabled: false,
    dpi_prevention: false,
    status: 'running',
    running: true,
    user_count: 1
  },
  {
    name: 'staging-proxy',
    port: 3130,
    https_enabled: true,
    dpi_prevention: false,
    status: 'stopped',
    running: false,
    user_count: 2
  }
];

export const MOCK_USERS: Record<string, string[]> = {
  'production-proxy': ['admin', 'user1', 'user2'],
  'development-proxy': ['developer'],
  'staging-proxy': ['tester1', 'tester2']
};

export const MOCK_LOGS = {
  access: `1706896800.000 127.0.0.1 TCP_TUNNEL/200 5120 CONNECT www.example.com:443 admin HIER_DIRECT/93.184.216.34 -
1706896805.000 127.0.0.1 TCP_TUNNEL/200 2048 CONNECT api.github.com:443 user1 HIER_DIRECT/140.82.121.6 -
1706896810.000 127.0.0.1 TCP_MISS/200 4096 GET http://www.example.com/test.html user2 HIER_DIRECT/93.184.216.34 text/html`,
  cache: `2024/02/02 12:00:00| Starting Squid Cache version 5.9
2024/02/02 12:00:00| Process ID 123
2024/02/02 12:00:00| Accepting HTTP connections at 0.0.0.0:3128
2024/02/02 12:00:00| Accepting HTTPS connections at 0.0.0.0:3128`
};

export const MOCK_CERTIFICATE_INFO: Record<string, CertificateInfo> = {
  'production-proxy': {
    status: 'valid',
    common_name: 'production-proxy.local',
    not_valid_before: '2024-01-01T00:00:00Z',
    not_valid_after: '2025-01-01T00:00:00Z',
    pem: '-----BEGIN CERTIFICATE-----\nMOCK_CERTIFICATE_DATA\n-----END CERTIFICATE-----'
  },
  'staging-proxy': {
    status: 'valid',
    common_name: 'staging-proxy.local',
    not_valid_before: '2024-01-01T00:00:00Z',
    not_valid_after: '2025-01-01T00:00:00Z',
    pem: '-----BEGIN CERTIFICATE-----\nMOCK_CERTIFICATE_DATA\n-----END CERTIFICATE-----'
  },
  'development-proxy': {
    status: 'missing'
  }
};

/**
 * Mock API responses with simulated delays
 */
export class MockApiClient {
  private instances: ProxyInstance[] = [...MOCK_INSTANCES];
  private delay = 300; // Simulate network delay

  private async simulateDelay(): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, this.delay));
  }

  async getInstances(): Promise<InstancesResponse> {
    await this.simulateDelay();
    return {
      instances: this.instances,
      count: this.instances.length
    };
  }

  async createInstance(payload: {
    name: string;
    port: number;
    https_enabled: boolean;
    dpi_prevention: boolean;
    users: { username: string; password: string }[];
  }): Promise<{ status: string }> {
    await this.simulateDelay();
    const newInstance: ProxyInstance = {
      name: payload.name,
      port: payload.port,
      https_enabled: payload.https_enabled,
      dpi_prevention: payload.dpi_prevention,
      status: 'running',
      running: true,
      user_count: payload.users.length
    };
    this.instances.push(newInstance);
    MOCK_USERS[payload.name] = payload.users.map((u) => u.username);
    return { status: 'success' };
  }

  async startInstance(name: string): Promise<{ status: string }> {
    await this.simulateDelay();
    const instance = this.instances.find((i) => i.name === name);
    if (instance) {
      instance.status = 'running';
      instance.running = true;
    }
    return { status: 'success' };
  }

  async stopInstance(name: string): Promise<{ status: string }> {
    await this.simulateDelay();
    const instance = this.instances.find((i) => i.name === name);
    if (instance) {
      instance.status = 'stopped';
      instance.running = false;
    }
    return { status: 'success' };
  }

  async deleteInstance(name: string): Promise<{ status: string }> {
    await this.simulateDelay();
    this.instances = this.instances.filter((i) => i.name !== name);
    delete MOCK_USERS[name];
    return { status: 'success' };
  }

  async updateInstance(
    name: string,
    payload: Partial<{ port: number; https_enabled: boolean; dpi_prevention: boolean }>
  ): Promise<{ status: string }> {
    await this.simulateDelay();
    const instance = this.instances.find((i) => i.name === name);
    if (instance) {
      if (payload.port !== undefined) instance.port = payload.port;
      if (payload.https_enabled !== undefined) instance.https_enabled = payload.https_enabled;
      if (payload.dpi_prevention !== undefined) instance.dpi_prevention = payload.dpi_prevention;
    }
    return { status: 'success' };
  }

  async getUsers(name: string): Promise<UserResponse> {
    await this.simulateDelay();
    const users = MOCK_USERS[name] || [];
    return { users: users.map((username) => ({ username })) };
  }

  async addUser(name: string, username: string): Promise<{ status: string }> {
    await this.simulateDelay();
    if (!MOCK_USERS[name]) {
      MOCK_USERS[name] = [];
    }
    if (!MOCK_USERS[name].includes(username)) {
      MOCK_USERS[name].push(username);
      const instance = this.instances.find((i) => i.name === name);
      if (instance && instance.user_count !== undefined) {
        instance.user_count++;
      }
    }
    return { status: 'success' };
  }

  async removeUser(name: string, username: string): Promise<{ status: string }> {
    await this.simulateDelay();
    if (MOCK_USERS[name]) {
      MOCK_USERS[name] = MOCK_USERS[name].filter((u) => u !== username);
      const instance = this.instances.find((i) => i.name === name);
      if (instance && instance.user_count !== undefined) {
        instance.user_count--;
      }
    }
    return { status: 'success' };
  }

  async getLogs(name: string, type: 'cache' | 'access'): Promise<string> {
    await this.simulateDelay();
    return MOCK_LOGS[type];
  }

  async clearLogs(): Promise<{ status: string }> {
    await this.simulateDelay();
    return { status: 'success' };
  }

  async getCertificateInfo(name: string): Promise<CertificateInfo> {
    await this.simulateDelay();
    return MOCK_CERTIFICATE_INFO[name] || { status: 'missing' };
  }

  async testConnectivity(): Promise<{ status: string; message?: string }> {
    await this.simulateDelay();
    return { status: 'success', message: 'Connection test successful' };
  }

  async regenerateCertificates(name: string): Promise<{ status: string }> {
    await this.simulateDelay();
    if (MOCK_CERTIFICATE_INFO[name]) {
      MOCK_CERTIFICATE_INFO[name] = {
        status: 'valid',
        common_name: `${name}.local`,
        not_valid_before: new Date().toISOString(),
        not_valid_after: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString(),
        pem: '-----BEGIN CERTIFICATE-----\nNEW_MOCK_CERTIFICATE_DATA\n-----END CERTIFICATE-----'
      };
    }
    return { status: 'success' };
  }
}

export const mockApiClient = new MockApiClient();
