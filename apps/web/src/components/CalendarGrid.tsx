'use client';
import { useState, useSyncExternalStore } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { useRemote } from '@/hooks/useRemote';
import { eventsApi } from '@/lib/api/endpoints';
import { calendarWindow, calendarCells, shiftDay, type CalendarView } from '@/lib/calendar';
import { campusFormat, fromCampusISO, toCampusISO } from '@/lib/campus-time';
import RemoteState from './RemoteState';
const subscribe = () => () => {};
const currentDay = () => fromCampusISO(new Date().toISOString()).date;
const serverDay = () => '';

export default function CalendarGrid() {
  const { token } = useAuth();
  const [anchor, setAnchor] = useState(''); const [view, setView] = useState<CalendarView>('Month');
  const [offset, setOffset] = useState(0);
  // Read the current campus date only after hydration, avoiding server/client date mismatch.
  const today = useSyncExternalStore(subscribe, currentDay, serverDay);
  const now = anchor || today || '2000-01-01';
  const window = calendarWindow(now, view);
  const remote = useRemote(token && (anchor || today) ? token + window.first + window.end + offset : null,
    signal => eventsApi.list(token!, { starts_after: toCampusISO(window.first, '00:00'), starts_before: toCampusISO(window.end, '00:00'), limit: 100, offset }, signal));
  const events = remote.data?.items ?? [];
  const days = view === 'Week' ? Array.from({ length: 7 }, (_, i) => shiftDay(window.first, i)) : calendarCells(now);
  function move(direction: number) {
    const date = new Date(now + 'T12:00:00Z');
    if (view === 'Week') date.setUTCDate(date.getUTCDate() + direction * 7);
    else { date.setUTCDate(1); date.setUTCMonth(date.getUTCMonth() + direction); }
    setAnchor(date.toISOString().slice(0, 10)); setOffset(0);
  }
  return <section className="mx-auto max-w-7xl p-4 md:p-8">
    <h1 className="text-3xl font-bold text-[#7a1b32]">Campus calendar</h1>
    <p className="my-3 text-sm">Times in Asia/Kolkata. Proposals are tentative; an empty calendar does not prove venue availability.</p>
    {(anchor || today) && <><div className="my-5 flex flex-wrap items-center gap-3">
      <button aria-label="Previous period" onClick={() => move(-1)}>←</button>
      <label>Period <input aria-label="Calendar date" type="date" value={now} onChange={e => { setAnchor(e.target.value); setOffset(0); }} className="rounded border p-2" /></label>
      <button aria-label="Next period" onClick={() => move(1)}>→</button>
      <select aria-label="Calendar view" value={view} onChange={e => { setView(e.target.value as CalendarView); setOffset(0); }} className="rounded border p-2">{['Month', 'Week', 'List'].map(v => <option key={v}>{v}</option>)}</select>
      <Link href="/plan" className="ml-auto rounded-xl bg-[#7a1b32] px-5 py-3 text-white">Plan an event</Link>
    </div>
    <RemoteState signedIn={Boolean(token)} {...remote} empty={events.length === 0} />
    {remote.data && <>{view === 'List' ? <div className="space-y-3">{events.map(event => <article key={event.id} className="rounded-xl border bg-white p-4"><Link className="font-bold underline" href={'/changes?eventId=' + event.id}>{event.title}</Link><p>{campusFormat(event.start_at)} – {campusFormat(event.end_at)}</p><p>{event.status} · Venue availability: {event.venue_availability}{event.synthetic ? ' · Synthetic demo' : ''}</p></article>)}</div>
      : <div className="grid grid-cols-1 gap-2 sm:grid-cols-7">{days.map(day => <div key={day} className={'min-h-32 rounded-lg border p-2 ' + (day.slice(0, 7) === now.slice(0, 7) ? 'bg-white' : 'bg-stone-100')}><p className="text-xs font-bold">{campusFormat(toCampusISO(day, '12:00'), { weekday: 'short', day: 'numeric', month: 'short' })}</p>{events.filter(event => fromCampusISO(event.start_at).date === day).map(event => <Link key={event.id} href={'/changes?eventId=' + event.id} className="my-2 block rounded bg-rose-50 p-2 text-xs"><strong>{event.title}</strong><p>{campusFormat(event.start_at, { timeStyle: 'short' })} · {event.status}</p>{event.synthetic && <p>Synthetic demo</p>}</Link>)}</div>)}</div>}
    <div className="my-4 flex items-center gap-4"><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 100))}>Previous records</button><span>{remote.data.total} records in period</span><button disabled={offset + 100 >= remote.data.total} onClick={() => setOffset(offset + 100)}>More records</button></div></>}
    </>}
  </section>;
}
