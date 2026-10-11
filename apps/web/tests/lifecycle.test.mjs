import test from 'node:test';
import assert from 'node:assert/strict';
import { allowedTransitions } from '../src/lib/lifecycle.ts';
test('transition controls require session roles and respect lifecycle edges', () => {
  const user = { campus_admin: false, email: 'admin@example.invalid', memberships: [{ club_id: 'club', role: 'ORGANIZER' }] };
  assert.deepEqual(allowedTransitions('DRAFT', 'club', user), ['PROPOSED']);
  assert.deepEqual(allowedTransitions('SUBMITTED', 'club', user), []);
  assert.deepEqual(allowedTransitions('DRAFT', 'other', user), []);
  assert.deepEqual(allowedTransitions('SUBMITTED', 'club', { ...user, campus_admin: true }), ['CONFIRMED', 'REJECTED', 'CANCELLED']);
  assert.deepEqual(allowedTransitions('CANCELLED', 'club', { ...user, campus_admin: true }), []);
});
