import { describe, expect, it } from 'vitest';

import { createInstanceSchema, testCredentialsSchema, userSchema } from '@/features/instances/validation';

const passwordField = 'password';

describe('createInstanceSchema', () => {
  it('requires name and valid port', () => {
    const result = createInstanceSchema.safeParse({
      name: '',
      port: 80,
      https_enabled: false
    });

    expect(result.success).toBe(false);
  });

  it('accepts https enabled when required fields are present', () => {
    const result = createInstanceSchema.safeParse({
      name: 'proxy-1',
      port: 3128,
      https_enabled: true
    });

    expect(result.success).toBe(true);
  });

  it('accepts squid proxy_type with default fields (backward compat)', () => {
    const result = createInstanceSchema.safeParse({
      name: 'squid-proxy',
      port: 3128,
      proxy_type: 'squid',
      https_enabled: false
    });

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.proxy_type).toBe('squid');
    }
  });

  it('defaults proxy_type to squid when omitted', () => {
    const result = createInstanceSchema.safeParse({
      name: 'default-type',
      port: 3128,
      https_enabled: false
    });

    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.proxy_type).toBe('squid');
    }
  });

  it('accepts tls_tunnel with valid forward_address', () => {
    const result = createInstanceSchema.safeParse({
      name: 'vpn-tunnel',
      port: 8443,
      proxy_type: 'tls_tunnel',
      https_enabled: false,
      forward_address: 'vpn.example.com:1194'
    });

    expect(result.success).toBe(true);
  });

  it('accepts tls_tunnel with forward_address and cover_domain', () => {
    const result = createInstanceSchema.safeParse({
      name: 'vpn-tunnel',
      port: 8443,
      proxy_type: 'tls_tunnel',
      https_enabled: false,
      forward_address: 'vpn.example.com:1194',
      cover_domain: 'mysite.example.com'
    });

    expect(result.success).toBe(true);
  });

  it('rejects tls_tunnel missing forward_address', () => {
    const result = createInstanceSchema.safeParse({
      name: 'vpn-tunnel',
      port: 8443,
      proxy_type: 'tls_tunnel',
      https_enabled: false
    });

    expect(result.success).toBe(false);
    if (!result.success) {
      const forwardIssue = result.error.issues.find(i => i.path.includes('forward_address'));
      expect(forwardIssue).toBeDefined();
      expect(forwardIssue?.message).toContain('VPN server destination is required');
    }
  });

  it('rejects invalid forward_address format', () => {
    const result = createInstanceSchema.safeParse({
      name: 'vpn-tunnel',
      port: 8443,
      proxy_type: 'tls_tunnel',
      https_enabled: false,
      forward_address: 'not_valid_format'
    });

    expect(result.success).toBe(false);
    if (!result.success) {
      const forwardIssue = result.error.issues.find(i => i.path.includes('forward_address'));
      expect(forwardIssue).toBeDefined();
      expect(forwardIssue?.message).toContain('hostname:port');
    }
  });

  it('rejects forward_address with spaces', () => {
    const result = createInstanceSchema.safeParse({
      name: 'vpn-tunnel',
      port: 8443,
      proxy_type: 'tls_tunnel',
      forward_address: 'my host:1194'
    });

    expect(result.success).toBe(false);
  });

  it('accepts squid type without forward_address (not required)', () => {
    const result = createInstanceSchema.safeParse({
      name: 'squid-proxy',
      port: 3128,
      proxy_type: 'squid',
      https_enabled: false
    });

    expect(result.success).toBe(true);
  });
});

describe('userSchema', () => {
  it('requires password length', () => {
    const result = userSchema.safeParse({ username: 'user', [passwordField]: '123' });
    expect(result.success).toBe(false);
  });
});

describe('testCredentialsSchema', () => {
  it('accepts empty target url', () => {
    const result = testCredentialsSchema.safeParse({
      username: 'user',
      [passwordField]: 'pw12345',
      target_url: ''
    });

    expect(result.success).toBe(true);
  });

  it('rejects invalid target url', () => {
    const result = testCredentialsSchema.safeParse({
      username: 'user',
      [passwordField]: 'pw12345',
      target_url: 'not-a-url'
    });

    expect(result.success).toBe(false);
  });
});
