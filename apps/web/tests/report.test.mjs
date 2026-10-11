import test from 'node:test';
import assert from 'node:assert/strict';
import { buildReport } from '../src/lib/report.ts';
test('report uses recorded facts and leaves unverified outcomes explicitly missing', () => {
  const event = { title: 'Test event', synthetic: true, revision: 2, status: 'DRAFT', start_at: '2026-10-11T04:30:00Z', end_at: '2026-10-11T05:30:00Z', resource_id: null, venue_availability: 'UNKNOWN', expected_attendance: 120, description: null };
  const report = buildReport(event);
  assert.match(report, /SYNTHETIC DEMO/);
  assert.match(report, /Actual attendance: \[not recorded\]/);
  assert.match(report, /120 \(a planning estimate/);
  assert.match(report, /Status: DRAFT/);
  assert.doesNotMatch(report, /approved|acknowledged|confirmed by/i);
});
