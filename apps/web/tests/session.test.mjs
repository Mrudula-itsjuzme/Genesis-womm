import test from 'node:test';
import assert from 'node:assert/strict';
import { restoreSession } from '../src/lib/session.ts';
test('session restoration rejects corrupt, expired and legacy identities', () => {
  assert.equal(restoreSession('{'), null);
  assert.equal(restoreSession(JSON.stringify({ access_token: 'x', user: {} })), null);
  assert.equal(restoreSession(JSON.stringify({ access_token: 'x', expires_at: '2020-01-01', user: { id: 'u', email: 'u@test', display_name: 'User', memberships: [], campus_admin: false } })), null);
  const session = { access_token: 'x', expires_at: '2099-01-01', user: { id: 'u', email: 'u@test', display_name: 'User', memberships: [], campus_admin: false } };
  assert.deepEqual(restoreSession(JSON.stringify(session)), session);
});
