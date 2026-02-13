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
    expect(fetchMock).toHaveBeenCalledWith('/api/hassio_ingress/test-token/', expect.any(Object));
  });
});

describe('requestJson error extraction (v1.6.4 regression tests)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    Object.defineProperty(window, 'location', {
      value: { pathname: '/api/hassio_ingress/test-token/' },
      writable: true
    });
  });

  it('extracts error message from "error" field in JSON response', async () => {
    // Bug: v1.6.3 and earlier showed raw JSON string to users
    // Fix: v1.6.4 extracts error/message/detail fields
    const errorResponse = new Response(
      JSON.stringify({ error: 'Invalid instance name' }),
      { status: 400, statusText: 'Bad Request' }
    );
    const fetchMock = vi.fn().mockResolvedValue(errorResponse);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    try {
      await requestJson('/api/instances');
      expect.fail('Should have thrown an error');
    } catch (err: any) {
      expect(err.message).toBe('Invalid instance name');
      expect(err.status).toBe(400);
    }
  });

  it('extracts error message from "message" field in JSON response', async () => {
    const errorResponse = new Response(
      JSON.stringify({ message: 'Port already in use' }),
      { status: 409, statusText: 'Conflict' }
    );
    const fetchMock = vi.fn().mockResolvedValue(errorResponse);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    try {
      await requestJson('/api/instances');
      expect.fail('Should have thrown an error');
    } catch (err: any) {
      expect(err.message).toBe('Port already in use');
      expect(err.status).toBe(409);
    }
  });

  it('extracts error message from "detail" field in JSON response', async () => {
    const errorResponse = new Response(
      JSON.stringify({ detail: 'Instance not found' }),
      { status: 404, statusText: 'Not Found' }
    );
    const fetchMock = vi.fn().mockResolvedValue(errorResponse);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    try {
      await requestJson('/api/instances/nonexistent');
      expect.fail('Should have thrown an error');
    } catch (err: any) {
      expect(err.message).toBe('Instance not found');
      expect(err.status).toBe(404);
    }
  });

  it('prefers "error" field over "message" when both present', async () => {
    const errorResponse = new Response(
      JSON.stringify({ error: 'Primary error', message: 'Secondary message' }),
      { status: 400, statusText: 'Bad Request' }
    );
    const fetchMock = vi.fn().mockResolvedValue(errorResponse);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    try {
      await requestJson('/api/instances');
      expect.fail('Should have thrown an error');
    } catch (err: any) {
      expect(err.message).toBe('Primary error');
    }
  });

  it('falls back to status text when JSON parsing fails', async () => {
    // Non-JSON error response (e.g., nginx 502 error page)
    const errorResponse = new Response(
      '<html><body>502 Bad Gateway</body></html>',
      { status: 502, statusText: 'Bad Gateway' }
    );
    const fetchMock = vi.fn().mockResolvedValue(errorResponse);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    try {
      await requestJson('/api/instances');
      expect.fail('Should have thrown an error');
    } catch (err: any) {
      // Should include status code and status text in fallback message
      expect(err.message).toContain('502');
      expect(err.message).toContain('Bad Gateway');
      expect(err.status).toBe(502);
    }
  });

  it('falls back to status text when response has no error fields', async () => {
    // JSON response but no error/message/detail fields
    const errorResponse = new Response(
      JSON.stringify({ someOtherField: 'value' }),
      { status: 500, statusText: 'Internal Server Error' }
    );
    const fetchMock = vi.fn().mockResolvedValue(errorResponse);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    try {
      await requestJson('/api/instances');
      expect.fail('Should have thrown an error');
    } catch (err: any) {
      expect(err.message).toContain('500');
      expect(err.message).toContain('Internal Server Error');
      expect(err.status).toBe(500);
    }
  });

  it('extracts plain text error when JSON has text content', async () => {
    // Plain text error response wrapped in quotes (edge case)
    const errorResponse = new Response(
      '"Plain text error message"',
      { status: 400, statusText: 'Bad Request' }
    );
    const fetchMock = vi.fn().mockResolvedValue(errorResponse);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    try {
      await requestJson('/api/instances');
      expect.fail('Should have thrown an error');
    } catch (err: any) {
      // Should extract text or fall back to status
      expect(err.message).toBeTruthy();
      expect(err.status).toBe(400);
    }
  });

  it('handles empty error response body gracefully', async () => {
    const errorResponse = new Response('', { status: 400, statusText: 'Bad Request' });
    const fetchMock = vi.fn().mockResolvedValue(errorResponse);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    try {
      await requestJson('/api/instances');
      expect.fail('Should have thrown an error');
    } catch (err: any) {
      expect(err.message).toContain('400');
      expect(err.message).toContain('Bad Request');
      expect(err.status).toBe(400);
    }
  });
});
