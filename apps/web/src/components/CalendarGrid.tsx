'use client';
import { useState, useSyncExternalStore } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { useRemote } from '@/hooks/useRemote';
import { eventsApi } from '@/lib/api/endpoints';
import { calendarWindow, calendarCells, shiftDay, type CalendarView } from '@/lib/calendar';
import { campusFormat, fromCampusISO, toCampusISO } from '@/lib/campus-time';
import RemoteState from './RemoteState';
import EventDetailModal from './EventDetailModal';
const subscribe = () => () => {};
const currentDay = () => fromCampusISO(new Date().toISOString()).date;
const serverDay = () => '';

function getStatusBadgeStyle(status: string) {
  switch (status) {
    case 'CONFIRMED':
      return 'bg-emerald-50 text-emerald-900 border-emerald-300';
    case 'PROPOSED':
      return 'bg-amber-50 text-amber-900 border-amber-300';
    case 'CANCELLED':
      return 'bg-stone-100 text-stone-500 border-stone-200 line-through';
    case 'DRAFT':
    default:
      return 'bg-blue-50 text-blue-900 border-blue-300';
  }
}

export default function CalendarGrid() {
  const { token } = useAuth();
  const [anchor, setAnchor] = useState(''); const [view, setView] = useState<CalendarView>('Month');
  const [offset, setOffset] = useState(0); const [selected, setSelected] = useState<{token: string; id: string} | null>(null);
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
    <p className="my-2 text-sm text-stone-600">Times in Asia/Kolkata. Proposals are tentative; an empty calendar does not prove venue availability.</p>
    <div className="my-3 flex flex-wrap items-center gap-2 text-xs">
      <span className="font-semibold text-stone-700">Status Guide:</span>
      <span className="inline-flex items-center gap-1 rounded border border-emerald-300 bg-emerald-50 px-2 py-0.5 font-medium text-emerald-800">● Confirmed Booking</span>
      <span className="inline-flex items-center gap-1 rounded border border-amber-300 bg-amber-50 px-2 py-0.5 font-medium text-amber-800">▲ Tentative Proposal</span>
      <span className="inline-flex items-center gap-1 rounded border border-blue-300 bg-blue-50 px-2 py-0.5 font-medium text-blue-800">◼ Draft</span>
      <span className="inline-flex items-center gap-1 rounded border border-stone-200 bg-stone-100 px-2 py-0.5 font-medium text-stone-500">✕ Cancelled</span>
    </div>
    {(anchor || today) && <><div className="my-5 flex flex-wrap items-center gap-3">
      <button aria-label="Previous period" onClick={() => move(-1)} className="rounded border px-3 py-1 font-bold hover:bg-stone-100">←</button>
      <label className="text-sm font-medium">Period <input aria-label="Calendar date" type="date" value={now} onChange={e => { setAnchor(e.target.value); setOffset(0); }} className="rounded border p-2 text-sm" /></label>
      <button aria-label="Next period" onClick={() => move(1)} className="rounded border px-3 py-1 font-bold hover:bg-stone-100">→</button>
      <select aria-label="Calendar view" value={view} onChange={e => { setView(e.target.value as CalendarView); setOffset(0); }} className="rounded border p-2 text-sm">{['Month', 'Week', 'List'].map(v => <option key={v}>{v}</option>)}</select>
      <Link href="/plan" className="ml-auto rounded-xl bg-[#7a1b32] px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-[#601426]">Plan an event</Link>
    </div>
    <RemoteState signedIn={Boolean(token)} {...remote} empty={events.length === 0} />
    {remote.data && <>{view === 'List' ? <div className="space-y-3">{events.map(event => <article key={event.id} className={`rounded-xl border p-4 shadow-sm ${getStatusBadgeStyle(event.status)}`}><button className="font-bold underline" onClick={() => setSelected({ token: token!, id: event.id })}>{event.title}</button><p className="text-sm mt-1">{campusFormat(event.start_at)} – {campusFormat(event.end_at)}</p><p className="text-xs mt-1 font-medium">{event.status} · Venue availability: {event.venue_availability}{event.synthetic ? ' · Synthetic demo' : ''}</p></article>)}</div>
      : <div className="grid grid-cols-1 gap-2 sm:grid-cols-7">{days.map(day => <div key={day} className={'min-h-32 rounded-lg border p-2 ' + (day.slice(0, 7) === now.slice(0, 7) ? 'bg-white' : 'bg-stone-100')}><p className="text-xs font-bold text-stone-700">{campusFormat(toCampusISO(day, '12:00'), { weekday: 'short', day: 'numeric', month: 'short' })}</p>{events.filter(event => fromCampusISO(event.start_at).date === day).map(event => <button key={event.id} onClick={() => setSelected({ token: token!, id: event.id })} className={`my-2 block w-full rounded border p-2 text-left text-xs transition hover:shadow-sm ${getStatusBadgeStyle(event.status)}`}><strong>{event.title}</strong><p className="mt-0.5">{campusFormat(event.start_at, { timeStyle: 'short' })} · {event.status}</p>{event.synthetic && <p className="text-[10px] opacity-75 mt-0.5">Synthetic demo</p>}</button>)}</div>)}</div>}
    <div className="my-4 flex items-center gap-4"><button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - 100))} className="rounded border px-3 py-1 text-sm disabled:opacity-50">Previous records</button><span className="text-sm font-medium">{remote.data.total} records in period</span><button disabled={offset + 100 >= remote.data.total} onClick={() => setOffset(offset + 100)} className="rounded border px-3 py-1 text-sm disabled:opacity-50">More records</button></div></>}
    </>}
    {selected && selected.token === token && <EventDetailModal key={token + selected.id} id={selected.id} close={() => setSelected(null)} />}
  </section>;
}
