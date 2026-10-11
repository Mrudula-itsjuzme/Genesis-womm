import { test, expect } from '@playwright/test';
import { gateway, event, eventId, session } from './fixtures';

test('organizers register dependencies and stage changes without applying them', async ({ page }) => {
  await gateway(page);
  const dependency = { id: 'item', event_id: eventId, title: 'Speaker logistics', kind: 'TASK', status: 'OPEN', field_paths: ['start_at'], needs_revalidation: false };
  let items: unknown[] = [], proposals: unknown[] = [], stages = 0;
  await page.route('**/dependencies', async route => {
    if (route.request().method() === 'POST') { expect(route.request().headers()['idempotency-key']).toBeTruthy(); items = [dependency]; return route.fulfill({ json: dependency }); }
    await route.fulfill({ json: { items, total: items.length } });
  });
  await page.route('**/impact', route => route.fulfill({ json: { event_id: eventId, base_revision: 1, changed_fields: ['start_at'], evaluated_as: 'DRAFT', advisory: true, conflicts: [], impact: [{ dependent_id: 'item', dependent_kind: 'TASK', title: dependency.title, status: 'OPEN', changed_fields: ['start_at'], reason: 'Start time changed', revalidation_required: true }] } }));
  await page.route('**/change-proposals*', async route => {
    if (route.request().method() === 'POST') {
      stages++; const payload = route.request().postDataJSON();
      expect(payload.expected_revision).toBe(1); expect(Object.keys(payload.changes)).toEqual(['start_at']);
      expect(route.request().headers()['idempotency-key']).toBeTruthy();
      const proposal = { id: 'proposal', event_id: eventId, base_revision: 1, reason: payload.reason, changes: payload.changes, impact: [], status: 'STAGED' };
      proposals = [proposal]; return route.fulfill({ json: proposal });
    }
    await route.fulfill({ json: { items: proposals, total: proposals.length, limit: 20, offset: 0 } });
  });
  await page.goto('/changes?eventId=' + eventId);
  await page.getByLabel('Dependency title').fill(dependency.title);
  await page.getByRole('button', { name: 'Record dependency' }).click();
  await expect(page.getByText('Dependency recorded.')).toBeVisible();
  await page.getByLabel('Change start (Asia/Kolkata)').fill('2026-10-18T11:00');
  await page.getByLabel('Change reason').fill('Speaker timing correction');
  await expect(page.getByText('Start time changed')).toBeVisible();
  expect(stages).toBe(0);
  await page.getByRole('button', { name: 'Stage change proposal' }).click();
  await expect(page.getByText('Speaker timing correction · STAGED')).toBeVisible();
  await expect(page.getByText('An administrator must apply this change.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Apply staged change' })).toHaveCount(0);
  expect(stages).toBe(1);
  await expect(page.getByText(/DRAFT.*Revision 1/)).toBeVisible();
});

test('administrator apply requires a click and stale errors retain the proposal', async ({ page }) => {
  await gateway(page, false);
  await page.addInitScript(value => localStorage.setItem('campuscue.session.v1', JSON.stringify(value)), { ...session, user: { ...session.user, campus_admin: true } });
  await page.route('**/dependencies', route => route.fulfill({ json: { items: [], total: 0 } }));
  await page.route('**/change-proposals*', route => route.fulfill({ json: { items: [{ id: 'proposal', base_revision: 1, reason: 'Saved timing correction', changes: { start_at: '2026-10-18T11:00:00+05:30' }, impact: [], status: 'STAGED' }], total: 1 } }));
  let applies = 0;
  await page.route('**/change-proposals/proposal/apply', async route => {
    applies++; expect(route.request().postDataJSON()).toEqual({ expected_revision: event.revision });
    expect(route.request().headers()['idempotency-key']).toBeTruthy();
    await route.fulfill({ status: 409, json: { code: 'REVISION_CONFLICT', message: 'Reload the current event revision.', details: [], request_id: 'stale-change' } });
  });
  await page.goto('/changes?eventId=' + eventId);
  await expect(page.getByRole('button', { name: 'Apply staged change' })).toBeVisible(); expect(applies).toBe(0);
  await page.getByRole('button', { name: 'Apply staged change' }).click();
  await expect(page.getByText(/Reload the current event revision/)).toBeVisible();
  await expect(page.getByText('Saved timing correction · STAGED')).toBeVisible(); expect(applies).toBe(1);
});
