import { describe, expect, it } from 'vitest';

import { createInstanceSchema, userSchema } from '@/features/instances/validation';

describe('createInstanceSchema', () => {
  it('requires name and valid port', () => {
    const result = createInstanceSchema.safeParse({
      name: '',
      port: 80,
      https_enabled: false,
      cert_params: { common_name: '', validity_days: 365, key_size: 2048 }
    });

    expect(result.success).toBe(false);
  });

  it('requires cert CN when https enabled', () => {
    const result = createInstanceSchema.safeParse({
      name: 'proxy-1',
      port: 3128,
      https_enabled: true,
      cert_params: { common_name: '', validity_days: 365, key_size: 2048 }
    });

    expect(result.success).toBe(false);
  });
});

describe('userSchema', () => {
  it('requires password length', () => {
    // pragma: allowlist secret
    const result = userSchema.safeParse({ username: 'user', password: '123' });
    expect(result.success).toBe(false);
  });
});
