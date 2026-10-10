export type CalendarView = 'Month' | 'Week' | 'List';
export function shiftDay(key: string, days: number) {
  const date = new Date(key + 'T12:00:00Z');
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}
export function calendarWindow(key: string, view: CalendarView) {
  const date = new Date(key + 'T12:00:00Z');
  if (view === 'Week') {
    const first = shiftDay(key, -((date.getUTCDay() + 6) % 7));
    return { first, end: shiftDay(first, 7) };
  }
  const first = key.slice(0, 7) + '-01';
  date.setUTCDate(1); date.setUTCMonth(date.getUTCMonth() + 1);
  return { first, end: date.toISOString().slice(0, 10) };
}
export function calendarCells(key: string) {
  const { first, end } = calendarWindow(key, 'Month');
  const start = calendarWindow(first, 'Week').first;
  const last = calendarWindow(shiftDay(end, -1), 'Week').end;
  const count = (Date.parse(last) - Date.parse(start)) / 86400000;
  return Array.from({ length: count }, (_, i) => shiftDay(start, i));
}
