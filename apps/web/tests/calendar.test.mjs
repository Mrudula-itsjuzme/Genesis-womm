import test from 'node:test';
import assert from 'node:assert/strict';
import { calendarWindow, calendarCells } from '../src/lib/calendar.ts';
test('calendar windows include complete campus-local days across year boundaries', () => {
  assert.deepEqual(calendarWindow('2026-12-31', 'Month'), { first: '2026-12-01', end: '2027-01-01' });
  assert.deepEqual(calendarWindow('2026-12-31', 'Week'), { first: '2026-12-28', end: '2027-01-04' });
  const cells = calendarCells('2026-02-14');
  assert.equal(cells.length, 35);
  assert.equal(cells[0], '2026-01-26');
  assert.equal(cells.at(-1), '2026-03-01');
});
