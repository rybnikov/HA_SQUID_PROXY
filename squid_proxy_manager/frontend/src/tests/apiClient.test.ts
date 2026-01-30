import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiFetch, requestJson } from '@/api/client';

describe('api client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(window, 'location', {
      value: { pathname: '/api/hassio_ingress/test-token/' },
      writable: true
    });
  });

  it('resolves api paths under ingress base', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    await apiFetch('api/instances');

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/hassio_ingress/test-token/api/instances',
      expect.any(Object)
    );
  });

  it('handles root status request', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response('{"status":"ok"}', { status: 200 }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await requestJson<{ status: string }>('/');

    expect(result.status).toBe('ok');
    expect(fetchMock).toHaveBeenCalledWith('/api/hassio_ingress/test-token', expect.any(Object));
  });
});
