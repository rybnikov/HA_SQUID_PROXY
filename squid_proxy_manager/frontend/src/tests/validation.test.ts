import { describe, expect, it } from 'vitest';

import { createInstanceSchema, testCredentialsSchema, userSchema } from '@/features/instances/validation';

const passwordField = 'password';

describe('createInstanceSchema', () => {
  it('requires name and valid port', () => {
    const result = createInstanceSchema.safeParse({
      name: '',
      port: 80,
      https_enabled: false,
      dpi_prevention: false
    });

    expect(result.success).toBe(false);
  });

  it('accepts https enabled when required fields are present', () => {
    const result = createInstanceSchema.safeParse({
      name: 'proxy-1',
      port: 3128,
      https_enabled: true,
      dpi_prevention: false
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
