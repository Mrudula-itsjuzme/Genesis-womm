import type { SessionOut } from '../types/core-api.ts';
export const SESSION_KEY = 'campuscue.session.v1';
export function restoreSession(raw: string | null): SessionOut | null {
  try {
    const value = JSON.parse(raw ?? 'null');
    if (!value || typeof value.access_token !== 'string' || !value.access_token || Date.parse(value.expires_at) <= Date.now() || !Number.isFinite(Date.parse(value.expires_at))) return null;
    const user = value.user;
    if (!user || typeof user.id !== 'string' || typeof user.email !== 'string' || typeof user.display_name !== 'string' || typeof user.campus_admin !== 'boolean' || !Array.isArray(user.memberships) || user.memberships.some((m: unknown) => !m || typeof m !== 'object' || !('club_id' in m) || !('role' in m))) return null;
    return value as SessionOut;
  } catch { return null; }
}
