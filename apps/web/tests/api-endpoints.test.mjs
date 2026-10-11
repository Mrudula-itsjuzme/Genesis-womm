import test from 'node:test';
import assert from 'node:assert/strict';
import { toCampusISO, fromCampusISO, validateEventPlan } from '../src/lib/campus-time.ts';
import { eventsApi, agentApi, changesApi, resourcesApi } from '../src/lib/api/endpoints.ts';

test('campus conversion handles UTC midnight and rejects invalid input', () => {
  assert.deepEqual(fromCampusISO('2026-10-18T20:00:00Z'), { date: '2026-10-19', time: '01:30' });
  assert.equal(toCampusISO('2026-10-18', '14:30'), '2026-10-18T14:30:00+05:30');
  assert.throws(() => toCampusISO('2026-02-30', '14:30'));
  assert.throws(() => toCampusISO('2026-10-18', '25:30'));
});

test('change requests preserve partial clears, revision and idempotency keys', async () => {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, init) => { calls.push({ url, body: JSON.parse(init.body), headers: init.headers }); return Response.json({}); };
  try {
    await changesApi.stage('token', 'event', { expected_revision: 3, changes: { resource_id: null }, reason: 'Clear venue' }, 'stage-key');
    await changesApi.apply('token', 'event', 'proposal', { expected_revision: 3 }, 'apply-key');
    assert.deepEqual(calls[0].body.changes, { resource_id: null });
    assert.equal(calls[0].headers.get('Idempotency-Key'), 'stage-key');
    assert.equal(calls[1].url, '/api/v1/events/event/change-proposals/proposal/apply');
    assert.equal(calls[1].body.expected_revision, 3);
    assert.equal(calls[1].headers.get('Idempotency-Key'), 'apply-key');
  } finally { globalThis.fetch = original; }
});
test('production validation rejects blank titles, backwards intervals and invalid attendance', () => {
  const event = { title: 'Hackathon', start_at: '2026-10-18T10:00:00+05:30', end_at: '2026-10-18T12:00:00+05:30', expected_attendance: 0 };
  assert.equal(validateEventPlan(event), null);
  assert.ok(validateEventPlan({ ...event, title: ' ' }));
  assert.ok(validateEventPlan({ ...event, end_at: event.start_at }));
  assert.ok(validateEventPlan({ ...event, expected_attendance: -1 }));
});
test('HTTP wrappers preserve contract payloads and use public candidate preview', async () => {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, init) => { calls.push({ url, body: JSON.parse(init.body), headers: init.headers }); return Response.json({}); };
  try {
    await eventsApi.preview('token', { club_id: 'club', title: 'New', start_at: 'a', end_at: 'b', resource_id: null });
    await eventsApi.transition('token', 'event', { target_status: 'SUBMITTED', expected_revision: 2 });
    await agentApi.chat('token', [{ role: 'user', content: 'Help' }]);
    await resourcesApi.createInterest('token', {
      category: 'Eeg kit',
      purpose: 'Prototype signal capture',
      preferred_date: '2026-10-20',
      start_time: '10:00',
      end_time: '12:00',
      requirements: null,
    });
    assert.equal(calls[0].url, '/api/v1/events/conflict-check');
    assert.equal(calls[0].body.resource_id, null);
    assert.equal(calls[1].body.target_status, 'SUBMITTED');
    assert.equal(calls[1].body.expected_revision, 2);
    assert.deepEqual(calls[2].body.messages, [{ role: 'user', content: 'Help' }]);
    assert.equal(calls[3].url, '/api/v1/resources/interests');
    assert.equal(calls[3].body.category, 'Eeg kit');
    assert.equal(calls[3].headers.get('Authorization'), 'Bearer token');
  } finally { globalThis.fetch = original; }
});
