import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MockApiClient, MOCK_INSTANCES } from '@/api/mockData';

// Use a fresh MockApiClient per test suite to avoid state leakage
let mockApiClient: MockApiClient;

describe('mock mode integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiClient = new MockApiClient();
  });

  it('should return expected mock instances', async () => {
    const result = await mockApiClient.getInstances();

    expect(result.instances).toContainEqual(
      expect.objectContaining({
        name: 'production-proxy',
        port: 3128,
        https_enabled: true,
        status: 'running'
      })
    );

    expect(result.instances).toContainEqual(
      expect.objectContaining({
        name: 'development-proxy',
        port: 3129,
        https_enabled: false
      })
    );
  });

  it('should create new instances in mock mode', async () => {
    const initialInstances = await mockApiClient.getInstances();
    const initialCount = initialInstances.count;

    await mockApiClient.createInstance({
      name: 'test-proxy',
      port: 3140,
      https_enabled: false,
      dpi_prevention: false,
      users: [{ username: 'testuser', password: 'testpass' }]
    });

    const updatedInstances = await mockApiClient.getInstances();
    expect(updatedInstances.count).toBe(initialCount + 1);
    expect(updatedInstances.instances).toContainEqual(
      expect.objectContaining({
        name: 'test-proxy',
        port: 3140
      })
    );
  });

  it('should start and stop instances', async () => {
    const result = await mockApiClient.stopInstance('production-proxy');
    expect(result.status).toBe('success');

    const instances = await mockApiClient.getInstances();
    const instance = instances.instances.find((i) => i.name === 'production-proxy');
    expect(instance?.status).toBe('stopped');
    expect(instance?.running).toBe(false);

    await mockApiClient.startInstance('production-proxy');
    const updatedInstances = await mockApiClient.getInstances();
    const startedInstance = updatedInstances.instances.find((i) => i.name === 'production-proxy');
    expect(startedInstance?.status).toBe('running');
    expect(startedInstance?.running).toBe(true);
  });

  it('should manage users in mock mode', async () => {
    const users = await mockApiClient.getUsers('production-proxy');
    expect(users.users.length).toBeGreaterThan(0);

    await mockApiClient.addUser('production-proxy', 'newuser');
    const updatedUsers = await mockApiClient.getUsers('production-proxy');
    expect(updatedUsers.users).toContainEqual({ username: 'newuser' });

    await mockApiClient.removeUser('production-proxy', 'newuser');
    const finalUsers = await mockApiClient.getUsers('production-proxy');
    expect(finalUsers.users).not.toContainEqual({ username: 'newuser' });
  });

  it('should return certificate info for instances', async () => {
    const certInfo = await mockApiClient.getCertificateInfo('production-proxy');
    expect(certInfo.status).toBe('valid');
    expect(certInfo.common_name).toBe('production-proxy.local');

    const noCert = await mockApiClient.getCertificateInfo('development-proxy');
    expect(noCert.status).toBe('missing');
  });
});

describe('mock mode TLS tunnel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiClient = new MockApiClient();
  });

  it('should include tls_tunnel instance (vpn-tunnel) in mock data', async () => {
    const result = await mockApiClient.getInstances();

    expect(result.instances).toContainEqual(
      expect.objectContaining({
        name: 'vpn-tunnel',
        proxy_type: 'tls_tunnel',
        port: 8443,
        forward_address: 'vpn.example.com:1194',
        cover_domain: 'mysite.example.com',
        status: 'running'
      })
    );
  });

  it('should return tls_tunnel snippet for tls_tunnel instance', async () => {
    const snippet = await mockApiClient.getOvpnSnippet('vpn-tunnel');

    expect(snippet).toContain('TLS Tunnel');
    expect(snippet).toContain('tls-crypt');
    expect(snippet).toContain('proto tcp');
    expect(snippet).not.toContain('http-proxy');
  });

  it('should return squid snippet for squid instance', async () => {
    const snippet = await mockApiClient.getOvpnSnippet('production-proxy');

    expect(snippet).toContain('Squid Proxy');
    expect(snippet).toContain('http-proxy');
    expect(snippet).toContain('3128');
    expect(snippet).not.toContain('tls-crypt');
  });

  it('should create tls_tunnel instance with proxy_type', async () => {
    const initialInstances = await mockApiClient.getInstances();
    const initialCount = initialInstances.count;

    await mockApiClient.createInstance({
      name: 'new-tunnel',
      port: 9443,
      proxy_type: 'tls_tunnel',
      https_enabled: false,
      dpi_prevention: false,
      users: [],
      forward_address: 'new-vpn.example.com:1194',
      cover_domain: 'cover.example.com'
    });

    const updatedInstances = await mockApiClient.getInstances();
    expect(updatedInstances.count).toBe(initialCount + 1);

    const newTunnel = updatedInstances.instances.find((i) => i.name === 'new-tunnel');
    expect(newTunnel).toBeDefined();
    expect(newTunnel?.proxy_type).toBe('tls_tunnel');
    expect(newTunnel?.forward_address).toBe('new-vpn.example.com:1194');
    expect(newTunnel?.cover_domain).toBe('cover.example.com');
    expect(newTunnel?.port).toBe(9443);
    expect(newTunnel?.status).toBe('running');
  });

  it('should update forward_address and cover_domain for tls_tunnel', async () => {
    await mockApiClient.updateInstance('vpn-tunnel', {
      forward_address: 'updated-vpn:2194',
      cover_domain: 'updated.example.com'
    });

    const instances = await mockApiClient.getInstances();
    const tunnel = instances.instances.find((i) => i.name === 'vpn-tunnel');
    expect(tunnel?.forward_address).toBe('updated-vpn:2194');
    expect(tunnel?.cover_domain).toBe('updated.example.com');
  });

  it('should return instance not found snippet for non-existent instance', async () => {
    const snippet = await mockApiClient.getOvpnSnippet('does-not-exist');
    expect(snippet).toContain('not found');
  });
});
