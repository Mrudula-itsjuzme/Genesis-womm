import test from 'node:test';
import assert from 'node:assert/strict';
import { apiClient, ApiResponseError } from '../src/lib/api/client.ts';

test('gateway sends auth, idempotency and tracing without leaking options', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async (input, init) => {
      assert.equal(input, '/api/v1/events?limit=3');
      const headers = new Headers(init?.headers);
      assert.equal(headers.get('Authorization'), 'Bearer token');
      assert.equal(headers.get('Idempotency-Key'), 'retry');
      assert.ok(headers.get('X-Request-ID'));
      assert.equal('token' in (init ?? {}), false);
      return Response.json({ items: [] });
    };
    assert.deepEqual(await apiClient('events', { token: 'token', idempotencyKey: 'retry', params: { limit: 3 } }), { items: [] });
  } finally { globalThis.fetch = original; }
});

test('preserves conflict details and server request id', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => Response.json({ code: 'STALE_REVISION', message: 'Refresh event', details: [{ actual: 2 }], request_id: 'server-id' }, { status: 409 });
    await assert.rejects(apiClient('events'), (error) => {
      assert.ok(error instanceof ApiResponseError);
      assert.equal(error.code, 'STALE_REVISION');
      assert.equal(error.requestId, 'server-id');
      assert.deepEqual(error.details, [{ actual: 2 }]);
      return true;
    });
  } finally { globalThis.fetch = original; }
});

test('multipart keeps browser boundary and 204 returns no body', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async (_, init) => {
      assert.equal(new Headers(init?.headers).has('Content-Type'), false);
      return new Response(null, { status: 204 });
    };
    assert.equal(await apiClient('documents', { method: 'POST', body: new FormData() }), undefined);
  } finally { globalThis.fetch = original; }
});

test('non-json gateway failures are explicit and do not invent scheduling conflicts', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => new Response('Bad Gateway', { status: 502 });
    await assert.rejects(apiClient('events'), (error) => error instanceof ApiResponseError && error.status === 502 && error.code === 'HTTP_ERROR');
  } finally { globalThis.fetch = original; }
});
