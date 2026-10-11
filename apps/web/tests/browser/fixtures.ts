import type { Page } from '@playwright/test';
export const club = '11111111-1111-4111-8111-111111111111';
export const eventId = '22222222-2222-4222-8222-222222222222';
export const session = { access_token: 'browser-test-token', expires_at: '2030-01-01T00:00:00Z', user: { id: '33333333-3333-4333-8333-333333333333', email: 'organizer@example.invalid', display_name: 'Demo Organizer', campus_admin: false, memberships: [{ club_id: club, club_name: 'Synthetic Club', role: 'ORGANIZER' }], synthetic: true } };
export const event = { id: eventId, club_id: club, title: 'Synthetic planning event', description: 'Test fixture', start_at: '2026-10-18T04:30:00Z', end_at: '2026-10-18T06:30:00Z', status: 'DRAFT', revision: 1, resource_id: null, expected_attendance: 10, audience_tags: [], venue_availability: 'UNKNOWN', synthetic: true, created_at: '2026-10-11T00:00:00Z', updated_at: '2026-10-11T00:00:00Z' };
export const check = { event_id: null, evaluated_as: 'DRAFT', has_blocking: false, conflicts: [], advisory: true, checked_at: '2026-10-11T00:00:00Z' };
export const action = { action_id: '44444444-4444-4444-8444-444444444444', type: 'CREATE_EVENT_DRAFT', summary: 'Review synthetic draft', status: 'PROPOSED', requires_human_review: true, target_event_id: null, expected_revision: null, payload: { title: 'Synthetic suggested event' }, conflicts: [], created_at: event.created_at };
export async function gateway(page: Page, authenticated = true) {
  if (authenticated) await page.addInitScript(value => localStorage.setItem('campuscue.session.v1', JSON.stringify(value)), session);
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    let body: unknown;
    if (path.endsWith('/auth/demo-login')) body = session;
    else if (path.endsWith('/resources')) body = { items: [], total: 0, limit: 100, offset: 0 };
    else if (path.endsWith('/conflict-check')) body = check;
    else if (path.endsWith('/events') && route.request().method() === 'GET') body = { items: [event], total: 1, limit: 50, offset: 0 };
    else if (path.endsWith('/events/' + eventId)) body = event;
    else return route.fulfill({ status: 404, json: { code: 'NOT_FOUND', message: 'Unconfigured browser fixture', details: [], request_id: 'browser-test' } });
    await route.fulfill({ json: body });
  });
}
