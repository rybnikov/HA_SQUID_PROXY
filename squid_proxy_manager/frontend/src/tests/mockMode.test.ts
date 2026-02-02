import { beforeEach, describe, expect, it, vi } from 'vitest';

import { mockApiClient } from '@/api/mockData';

describe('mock mode integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
