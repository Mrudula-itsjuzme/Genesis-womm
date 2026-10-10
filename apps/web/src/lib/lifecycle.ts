import type { EventStatus, UserOut } from '../types/core-api.ts';
const edges: Record<EventStatus, EventStatus[]> = {
  DRAFT: ['PROPOSED', 'CANCELLED'], PROPOSED: ['SUBMITTED', 'REJECTED', 'CANCELLED'],
  SUBMITTED: ['CONFIRMED', 'REJECTED', 'CANCELLED'], CONFIRMED: ['COMPLETED', 'CANCELLED'],
  COMPLETED: [], REJECTED: [], CANCELLED: [],
};
export function allowedTransitions(status: EventStatus, club: string, user: UserOut) {
  const role = user.memberships?.find(m => m.club_id === club)?.role;
  return edges[status].filter(target => {
    if (user.campus_admin) return true;
    if (target === 'CONFIRMED' || target === 'REJECTED') return false;
    if (target === 'CANCELLED' || target === 'COMPLETED') return role === 'CLUB_ADMIN';
    return role === 'ORGANIZER' || role === 'CLUB_ADMIN';
  });
}
