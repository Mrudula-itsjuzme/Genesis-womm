import type { EventCreate } from '../types/core-api.ts';

export function fromCampusISO(iso: string): { date: string; time: string } {
  const date = new Date(iso);
  if (!Number.isFinite(date.getTime())) throw new Error('Invalid date or time.');
  const shifted = new Date(date.getTime() + 330 * 60_000).toISOString();
  return { date: shifted.slice(0, 10), time: shifted.slice(11, 16) };
}
export function toCampusISO(date: string, time: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^\d{2}:\d{2}$/.test(time)) throw new Error('Enter a valid date and time.');
  const value = `${date}T${time}:00+05:30`;
  const parts = fromCampusISO(value);
  if (parts.date !== date || parts.time !== time) throw new Error('Enter a valid date and time.');
  return value;
}
export function campusFormat(iso: string, options: Intl.DateTimeFormatOptions = { dateStyle: 'medium', timeStyle: 'short' }) {
  return new Intl.DateTimeFormat('en-IN', { ...options, timeZone: 'Asia/Kolkata' }).format(new Date(iso));
}
export function validateEventPlan(event: Pick<EventCreate, 'title' | 'start_at' | 'end_at' | 'expected_attendance'>): string | null {
  if (!event.title.trim() || event.title.length > 200) return 'Enter a title of 1–200 characters.';
  const start = Date.parse(event.start_at), end = Date.parse(event.end_at);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return 'End time must be after start time.';
  if (event.expected_attendance != null && (!Number.isInteger(event.expected_attendance) || event.expected_attendance < 0)) return 'Attendance must be a non-negative integer.';
  return null;
}
