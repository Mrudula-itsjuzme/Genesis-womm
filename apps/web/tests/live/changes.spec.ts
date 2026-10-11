import { test, expect } from '@playwright/test';

test('real changes persist and admin apply revalidates registered work', async ({ page }) => {
  const login = await page.request.post('/api/v1/auth/demo-login', { data: { email: 'organizer@example.invalid' } });
  expect(login.ok()).toBe(true);
  const session = await login.json(), headers = { Authorization: 'Bearer ' + session.access_token };
  const created = await page.request.post('/api/v1/events', { headers, data: {
    club_id: session.user.memberships[0].club_id, title: 'Synthetic change QA ' + Date.now(),
    start_at: '2041-10-18T10:00:00+05:30', end_at: '2041-10-18T12:00:00+05:30',
  } });
  expect(created.status()).toBe(201);
  const event = (await created.json()).event;
  await page.addInitScript(value => {
    if (!localStorage.getItem('campuscue.session.v1')) localStorage.setItem('campuscue.session.v1', JSON.stringify(value));
  }, session);
  await page.goto('/changes?eventId=' + event.id);
  await page.getByLabel('Dependency title').fill('Synthetic speaker logistics');
  await page.getByRole('button', { name: 'Record dependency' }).click();
  await expect(page.getByText('Dependency recorded.')).toBeVisible();
  await page.getByLabel('Change start (Asia/Kolkata)').fill('2041-10-18T11:00');
  await page.getByLabel('Change reason').fill('Synthetic schedule correction');
  await page.getByRole('button', { name: 'Stage change proposal' }).click();
  await expect(page.getByText('Synthetic schedule correction · STAGED')).toBeVisible();
  const base = '/api/v1/events/' + event.id;
  const saved = await page.request.get(base + '/change-proposals', { headers });
  const proposal = (await saved.json()).items[0];
  const unchanged = await page.request.get(base, { headers });
  expect((await unchanged.json()).revision).toBe(1);
  const forbidden = await page.request.post(base + `/change-proposals/${proposal.id}/apply`, { headers, data: { expected_revision: 1 } });
  expect(forbidden.status()).toBe(403);
  const adminLogin = await page.request.post('/api/v1/auth/demo-login', { data: { email: 'campus-admin@example.invalid' } });
  const admin = await adminLogin.json();
  await page.evaluate(value => localStorage.setItem('campuscue.session.v1', JSON.stringify(value)), admin);
  await page.reload();
  await page.getByRole('button', { name: 'Apply staged change' }).click();
  await expect(page.getByText(/DRAFT.*Revision 2/)).toBeVisible();
  await expect(page.getByText('Synthetic schedule correction · APPLIED')).toBeVisible();
  const items = await page.request.get(base + '/dependencies', { headers });
  expect((await items.json()).items[0].needs_revalidation).toBe(true);
  const changed = await page.request.get(base, { headers });
  expect(new Date((await changed.json()).start_at).toISOString()).toBe('2041-10-18T05:30:00.000Z');
  const stale = await page.request.post(base + '/impact', { headers, data: { expected_revision: 1, changes: { expected_attendance: 20 } } });
  expect(stale.status()).toBe(409);
  const cancelled = await page.request.post(base + '/transitions', { headers: { Authorization: 'Bearer ' + admin.access_token }, data: { target_status: 'CANCELLED', expected_revision: 2 } });
  expect(cancelled.ok()).toBe(true);
});
