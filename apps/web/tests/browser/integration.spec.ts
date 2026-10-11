import { test, expect } from '@playwright/test';
import { gateway, event, eventId, check, session } from './fixtures';

test('planner previews unsaved schedules and sends an idempotent campus-time draft', async ({ page }) => {
  await gateway(page);
  let previewCalls = 0; let createCalls = 0;
  await page.route('**/api/v1/events/conflict-check', async route => { previewCalls++; expect(route.request().postDataJSON().start_at).toBe('2026-10-18T10:00:00+05:30'); await route.fulfill({ json: check }); });
  await page.route('**/api/v1/events', async route => { if (route.request().method() === 'GET') return route.fallback(); createCalls++; expect(route.request().headers()['idempotency-key']).toBeTruthy(); expect(route.request().postDataJSON().title).toBe('Browser draft'); await route.fulfill({ json: { event: { ...event, title: 'Browser draft' }, conflicts: [] } }); });
  await page.goto('/plan');
  await page.getByLabel('Event title').fill('Browser draft'); await page.getByLabel('Start date', { exact: true }).fill('2026-10-18'); await page.getByLabel('Start time', { exact: true }).fill('10:00'); await page.getByLabel('End time', { exact: true }).fill('12:00');
  await expect(page.getByText('No recorded conflicts found.')).toBeVisible(); expect(previewCalls).toBeGreaterThan(0); expect(createCalls).toBe(0);
  await page.getByRole('button', { name: 'Save event draft' }).click(); await expect(page.getByText('Saved Browser draft')).toBeVisible(); expect(createCalls).toBe(1); await expect(page.getByLabel('Event title')).toBeDisabled();
});

test('calendar loads month/week/list and opens a real detail dialog', async ({ page }) => {
  await gateway(page); await page.goto('/calendar'); await page.getByLabel('Calendar date').fill('2026-10-18');
  await page.getByLabel('Calendar view').selectOption('List'); await page.getByRole('button', { name: event.title, exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible(); await expect(page.getByRole('dialog').getByText('Expected attendance: 10')).toBeVisible();
  await page.keyboard.press('Escape'); await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByLabel('Calendar view').selectOption('Week'); await expect(page.getByRole('button', { name: /Synthetic planning event/ })).toBeVisible();
});

test('proposal upload survives download dependency failure', async ({ page }) => {
  await gateway(page);
  await page.route('**/proposals', route => route.fulfill({ json: { id: 'proposal-id', event_id: eventId, club_id: event.club_id, revision: 1, status: 'SUBMITTED', title: 'Proposal test', minio_key: 'test.pdf', submitted_at: event.created_at } }));
  await page.route('**/download-url', route => route.fulfill({ status: 503, json: { code: 'DEPENDENCY_UNAVAILABLE', message: 'Storage unavailable', details: [], request_id: 'storage-request' } }));
  await page.goto('/changes?eventId=' + eventId); await page.getByLabel('Document title').fill('Proposal test');
  await page.getByLabel('PDF file').setInputFiles({ name: 'test.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF-1.7 browser fixture') });
  await page.getByRole('button', { name: 'Upload proposal' }).click(); await expect(page.getByText('Saved Proposal test')).toBeVisible();
  await page.getByRole('button', { name: 'Get fresh download link' }).click(); await expect(page.getByText(/upload is saved, but/)).toBeVisible(); await expect(page.getByText('Saved Proposal test')).toBeVisible();
});

test('assistant preserves reply citations and multi-turn history without automatic actions', async ({ page }) => {
  await gateway(page); let calls = 0;
  await page.route('**/agent/chat', async route => { calls++; const body = route.request().postDataJSON(); expect(body.messages.length).toBe(calls === 1 ? 1 : 3); await route.fulfill({ json: { message: 'Evidence-based response ' + calls, request_id: 'chat-request', citations: [{ evidence_id: 'evidence-' + calls, document_id: 'doc', title: 'Synthetic policy', source_url: 'https://example.org/policy.pdf', page_start: 2, page_end: 2, excerpt: 'Exact fixture excerpt', document_version: 'v1' }], proposed_actions: [], trace: [] } }); });
  await page.goto('/policy'); await page.getByLabel('Policy question').fill('What approvals are recorded?'); await page.getByRole('button', { name: 'Ask CampusCue', exact: true }).click(); await expect(page.getByText('Evidence-based response 1')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Open source' })).toHaveAttribute('href', 'https://example.org/policy.pdf#page=2');
  await page.getByLabel('Policy question').fill('And venue allocation?'); await page.getByRole('button', { name: 'Ask CampusCue', exact: true }).click(); await expect(page.getByText('Evidence-based response 2')).toBeVisible(); await expect(page.getByRole('link', { name: 'Open source' })).toHaveCount(2);
});

test('report drafts remain editable and user-scoped', async ({ page }) => {
  await gateway(page); await page.goto('/reports'); await page.getByRole('combobox', { name: 'Event', exact: true }).selectOption(eventId);
  await expect(page.getByLabel('Report text')).toHaveValue(/Actual attendance: \[not recorded\]/); await page.getByLabel('Report text').fill('Verified organizer edit'); await page.getByRole('button', { name: 'Save local draft' }).click();
  await page.getByRole('button', { name: 'Regenerate from record' }).click(); await page.getByRole('button', { name: 'Restore local draft' }).click(); await expect(page.getByLabel('Report text')).toHaveValue('Verified organizer edit');
});

test('mobile navigation works and backend failures never display mock events', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await gateway(page);
  await page.route('**/api/v1/events*', route => route.fulfill({ status: 503, json: { code: 'DEPENDENCY_UNAVAILABLE', message: 'Core unavailable', details: [], request_id: 'offline-request' } }));
  await page.goto('/'); await expect(page.getByText(/Core unavailable/).first()).toBeVisible(); await expect(page.getByText('WOMM Orientation')).not.toBeVisible();
  await page.getByRole('button', { name: 'Open navigation' }).click(); await page.getByRole('navigation', { name: 'Mobile navigation' }).getByRole('link', { name: 'Reports' }).click(); await expect(page).toHaveURL(/reports/);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('proposal lookup rejects a document belonging to another event', async ({ page }) => {
  await gateway(page);
  await page.route('**/api/v1/proposals/known-id', route => route.fulfill({ json: { id: 'known-id', event_id: 'other-event', club_id: event.club_id, revision: 1, status: 'SUBMITTED', title: 'Wrong event', minio_key: 'test.pdf' } }));
  await page.goto('/changes?eventId=' + eventId);
  await page.getByLabel('Existing proposal ID').fill('known-id');
  await page.getByRole('button', { name: 'Load proposal', exact: true }).click();
  await expect(page.getByText('This proposal belongs to another event or club.')).toBeVisible();
  await expect(page.getByText('Saved Wrong event')).not.toBeVisible();
});

test('expired sessions clear protected records and identity', async ({ page }) => {
  await gateway(page);
  await page.route('**/api/v1/events*', route => route.fulfill({ status: 401, json: { code: 'UNAUTHORIZED', message: 'Session expired', details: [], request_id: 'expired-request' } }));
  await page.goto('/calendar');
  await expect.poll(() => page.evaluate(() => localStorage.getItem('campuscue.session.v1'))).toBeNull();
  await expect(page.getByText(event.title)).not.toBeVisible();
  await expect(page.getByRole('button', { name: 'Sign out' })).not.toBeVisible();
});

test('campus administrators can reopen and review a saved proposal', async ({ page }) => {
  await gateway(page, false);
  await page.addInitScript(value => localStorage.setItem('campuscue.session.v1', JSON.stringify(value)), { ...session, user: { ...session.user, campus_admin: true } });
  await page.route('**/api/v1/proposals/known-id', route => route.fulfill({ json: { id: 'known-id', event_id: eventId, club_id: event.club_id, revision: 1, status: 'SUBMITTED', title: 'Reopened proposal', minio_key: 'test.pdf' } }));
  await page.route('**/api/v1/proposals/known-id/status', async route => { expect(route.request().postDataJSON().action).toBe('request_revision'); await route.fulfill({ json: { id: 'known-id', event_id: eventId, club_id: event.club_id, revision: 1, status: 'REVISION_REQUESTED', title: 'Reopened proposal', minio_key: 'test.pdf' } }); });
  await page.goto('/changes?eventId=' + eventId);
  await page.getByLabel('Existing proposal ID').fill('known-id'); await page.getByRole('button', { name: 'Load proposal', exact: true }).click();
  await page.getByLabel('Review note').fill('Please include the agenda'); await page.getByRole('button', { name: 'request revision', exact: true }).click();
  await expect(page.getByText(/Saved Reopened proposal.*REVISION_REQUESTED/)).toBeVisible();
});
