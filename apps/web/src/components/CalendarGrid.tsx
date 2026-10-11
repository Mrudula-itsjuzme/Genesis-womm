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
      return 'bg-emerald-50/90 text-emerald-950 border-emerald-300 border-l-4 border-l-emerald-600';
    case 'PROPOSED':
      return 'bg-amber-50/90 text-amber-950 border-amber-300 border-l-4 border-l-amber-600';
    case 'CANCELLED':
      return 'bg-stone-100 text-stone-500 border-stone-200 line-through';
    case 'DRAFT':
    default:
      return 'bg-blue-50/90 text-blue-950 border-blue-300 border-l-4 border-l-blue-600';
  }
}

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function CalendarGrid() {
  const { token } = useAuth();
  const [anchor, setAnchor] = useState('');
  const [view, setView] = useState<CalendarView>('Month');
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<{ token: string; id: string } | null>(null);

  // Read the current campus date only after hydration, avoiding server/client date mismatch.
  const today = useSyncExternalStore(subscribe, currentDay, serverDay);
  const now = anchor || today || '2000-01-01';
  const window = calendarWindow(now, view);
  const remote = useRemote(
    token && (anchor || today) ? token + window.first + window.end + offset : null,
    signal =>
      eventsApi.list(
        token!,
        {
          starts_after: toCampusISO(window.first, '00:00'),
          starts_before: toCampusISO(window.end, '00:00'),
          limit: 100,
          offset,
        },
        signal
      )
  );
  const events = remote.data?.items ?? [];
  const days = view === 'Week' ? Array.from({ length: 7 }, (_, i) => shiftDay(window.first, i)) : calendarCells(now);

  const monthTitle = now
    ? campusFormat(toCampusISO(now.slice(0, 7) + '-01', '12:00'), { month: 'long', year: 'numeric' })
    : 'Campus Calendar';

  function move(direction: number) {
    const date = new Date(now + 'T12:00:00Z');
    if (view === 'Week') date.setUTCDate(date.getUTCDate() + direction * 7);
    else {
      date.setUTCDate(1);
      date.setUTCMonth(date.getUTCMonth() + direction);
    }
    setAnchor(date.toISOString().slice(0, 10));
    setOffset(0);
  }

  return (
    <section className="mx-auto w-full p-2 md:p-4">
      {/* Header row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[#7a1b32]">Campus calendar</h1>
          <p className="mt-1 text-sm text-stone-600">Times in Asia/Kolkata. Proposals are tentative; an empty calendar does not prove venue availability.</p>
        </div>
        <Link
          href="/plan"
          className="rounded-[10px] bg-[#7a1b32] px-4 py-2 text-xs font-semibold text-white shadow-sm transition-all duration-150 ease-out hover:bg-[#601426] active:scale-[0.98]"
        >
          Plan an event
        </Link>
      </div>

      {/* Status Legend */}
      <div className="my-3 flex flex-wrap items-center gap-2 text-xs">
        <span className="font-semibold text-stone-700">Status Guide:</span>
        <span className="inline-flex items-center gap-1.5 rounded-[6px] border border-emerald-300 bg-emerald-50 px-2 py-0.5 font-medium text-emerald-800">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-600"></span> Confirmed Booking
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-[6px] border border-amber-300 bg-amber-50 px-2 py-0.5 font-medium text-amber-800">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-600"></span> Tentative Proposal
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-[6px] border border-blue-300 bg-blue-50 px-2 py-0.5 font-medium text-blue-800">
          <span className="h-1.5 w-1.5 rounded-full bg-blue-600"></span> Draft
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-[6px] border border-stone-200 bg-stone-100 px-2 py-0.5 font-medium text-stone-500">
          ✕ Cancelled
        </span>
      </div>

      {(anchor || today) && (
        <>
          {/* Controls Bar */}
          <div className="my-4 flex flex-wrap items-center justify-between gap-3 rounded-[10px] border border-stone-200/80 bg-white/90 p-3 shadow-xs backdrop-blur-xl">
            <div className="flex flex-wrap items-center gap-2.5">
              <h2 className="text-xl font-bold tracking-tight text-stone-900 min-w-[150px]">{monthTitle}</h2>
              <div className="flex items-center gap-1 rounded-[8px] border border-stone-200 bg-stone-50 p-1">
                <button
                  aria-label="Previous period"
                  onClick={() => move(-1)}
                  className="rounded-[6px] px-2 py-1 text-xs font-bold text-stone-700 transition hover:bg-stone-200 active:scale-[0.95]"
                >
                  ←
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAnchor(today || '');
                    setOffset(0);
                  }}
                  className="rounded-[6px] px-2 py-1 text-xs font-semibold text-[#7a1b32] transition hover:bg-rose-50 active:scale-[0.95]"
                >
                  Today
                </button>
                <button
                  aria-label="Next period"
                  onClick={() => move(1)}
                  className="rounded-[6px] px-2 py-1 text-xs font-bold text-stone-700 transition hover:bg-stone-200 active:scale-[0.95]"
                >
                  →
                </button>
              </div>
              <label className="flex items-center gap-1 text-xs font-medium text-stone-600">
                Period
                <input
                  aria-label="Calendar date"
                  type="date"
                  value={now}
                  onChange={e => {
                    setAnchor(e.target.value);
                    setOffset(0);
                  }}
                  className="rounded-[8px] border border-stone-200 bg-white p-1 text-xs text-stone-800 transition focus:border-[#7a1b32] focus:outline-none"
                />
              </label>
            </div>

            <div className="flex items-center gap-2">
              <select
                aria-label="Calendar view"
                value={view}
                onChange={e => {
                  setView(e.target.value as CalendarView);
                  setOffset(0);
                }}
                className="rounded-[8px] border border-stone-300/80 bg-white px-2.5 py-1 text-xs font-semibold text-stone-800 shadow-xs transition focus:border-[#7a1b32] focus:outline-none"
              >
                {['Month', 'Week', 'List'].map(v => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </div>
          </div>

          <RemoteState signedIn={Boolean(token)} {...remote} empty={events.length === 0} />

          {remote.data && (
            <>
              {view === 'List' ? (
                <div className="space-y-2.5">
                  {events.length === 0 ? (
                    <p className="rounded-[10px] border border-stone-200/80 bg-white p-8 text-center text-sm text-stone-500">
                      No events recorded in this period.
                    </p>
                  ) : (
                    events.map(event => (
                      <article
                        key={event.id}
                        className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-[10px] border p-4 shadow-xs transition-all hover:shadow-sm ${getStatusBadgeStyle(
                          event.status
                        )}`}
                      >
                        <div>
                          <button
                            className="text-base font-bold text-stone-900 hover:text-[#7a1b32] hover:underline text-left"
                            onClick={() => setSelected({ token: token!, id: event.id })}
                          >
                            {event.title}
                          </button>
                          <p className="mt-1 text-xs font-medium text-stone-600">
                            🕒 {campusFormat(event.start_at)} – {campusFormat(event.end_at)}
                          </p>
                          <p className="mt-0.5 text-xs text-stone-500">
                            Status: {event.status}
                          </p>
                        </div>
                        <span className="self-start sm:self-center rounded-[6px] bg-white/90 border border-stone-200 px-2.5 py-1 text-xs font-bold text-stone-700 shadow-xs">
                          {event.status}
                        </span>
                      </article>
                    ))
                  )}
                </div>
              ) : view === 'Week' ? (
                <div className="overflow-x-auto rounded-[10px] border border-stone-200/80 bg-white/95 shadow-sm backdrop-blur-xl">
                  <div className="min-w-[760px]">
                    <div className="grid grid-cols-7 border-b border-stone-200/80 bg-stone-50/70 text-center text-xs font-semibold text-stone-600">
                      {days.map(day => (
                        <div key={day} className="py-2.5">
                          <span className="block text-[11px] font-medium text-stone-500">
                            {campusFormat(toCampusISO(day, '12:00'), { weekday: 'short' })}
                          </span>
                          <span
                            className={
                              'inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold mt-0.5 ' +
                              (day === today ? 'bg-[#7a1b32] text-white shadow-xs' : 'text-stone-800')
                            }
                          >
                            {parseInt(day.slice(8, 10), 10)}
                          </span>
                        </div>
                      ))}
                    </div>
                    <div className="grid grid-cols-7 divide-x divide-stone-200/60 min-h-[360px]">
                      {days.map(day => {
                        const dayEvents = events.filter(event => fromCampusISO(event.start_at).date === day);
                        return (
                          <div key={day} className="p-2 space-y-2 bg-white">
                            {dayEvents.map(event => (
                              <button
                                key={event.id}
                                onClick={() => setSelected({ token: token!, id: event.id })}
                                className={`w-full rounded-[8px] border p-2 text-left text-xs transition-all hover:shadow-xs active:scale-[0.98] ${getStatusBadgeStyle(
                                  event.status
                                )}`}
                              >
                                <strong className="block truncate text-xs font-semibold">{event.title}</strong>
                                <p className="mt-1 text-[11px] text-stone-600">
                                  {campusFormat(event.start_at, { timeStyle: 'short' })} · {event.status}
                                </p>
                              </button>
                            ))}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="overflow-x-auto rounded-[10px] border border-stone-200/80 bg-white/95 shadow-sm backdrop-blur-xl">
                  <div className="min-w-[760px]">
                    <div className="grid grid-cols-7 border-b border-stone-200/80 bg-stone-50/70 text-center text-xs font-semibold text-stone-600">
                      {WEEKDAYS.map(w => (
                        <div key={w} className="py-2.5 tracking-wide uppercase text-[11px]">
                          {w}
                        </div>
                      ))}
                    </div>
                    <div className="grid grid-cols-7 divide-x divide-y divide-stone-200/60">
                      {days.map(day => {
                        const isToday = day === today;
                        const isCurrentMonth = day.slice(0, 7) === now.slice(0, 7);
                        const dateNumber = parseInt(day.slice(8, 10), 10);
                        const dayEvents = events.filter(event => fromCampusISO(event.start_at).date === day);
                        return (
                          <div
                            key={day}
                            className={
                              'min-h-[115px] p-2 transition-colors ' +
                              (isCurrentMonth ? 'bg-white' : 'bg-stone-50/60 text-stone-400')
                            }
                          >
                            <div className="flex items-center justify-between mb-1.5">
                              <span
                                className={
                                  'flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ' +
                                  (isToday
                                    ? 'bg-[#7a1b32] text-white shadow-xs'
                                    : isCurrentMonth
                                    ? 'text-stone-800'
                                    : 'text-stone-400')
                                }
                              >
                                {dateNumber}
                              </span>
                              {day.slice(8, 10) === '01' && (
                                <span className="text-[10px] font-bold uppercase text-stone-400 tracking-wider">
                                  {campusFormat(toCampusISO(day, '12:00'), { month: 'short' })}
                                </span>
                              )}
                            </div>
                            <div className="space-y-1">
                              {dayEvents.map(event => (
                                <button
                                  key={event.id}
                                  onClick={() => setSelected({ token: token!, id: event.id })}
                                  className={
                                    'block w-full truncate rounded-[6px] border px-2 py-1 text-left text-xs transition-all hover:shadow-xs active:scale-[0.98] ' +
                                    getStatusBadgeStyle(event.status)
                                  }
                                >
                                  <strong className="block truncate font-semibold text-[11px]">{event.title}</strong>
                                  <span className="block text-[10px] opacity-80">
                                    {campusFormat(event.start_at, { timeStyle: 'short' })} · {event.status}
                                  </span>
                                </button>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}

              <div className="my-4 flex items-center justify-between rounded-[10px] border border-stone-200/80 bg-white p-3 shadow-xs">
                <button
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - 100))}
                  className="rounded-[8px] border border-stone-300 bg-white px-3 py-1.5 text-xs font-semibold text-stone-700 shadow-xs transition hover:bg-stone-50 active:scale-[0.98] disabled:opacity-40"
                >
                  Previous records
                </button>
                <span className="text-xs font-medium text-stone-600">{remote.data.total} records in period</span>
                <button
                  disabled={offset + 100 >= remote.data.total}
                  onClick={() => setOffset(offset + 100)}
                  className="rounded-[8px] border border-stone-300 bg-white px-3 py-1.5 text-xs font-semibold text-stone-700 shadow-xs transition hover:bg-stone-50 active:scale-[0.98] disabled:opacity-40"
                >
                  More records
                </button>
              </div>
            </>
          )}
        </>
      )}
      {selected && selected.token === token && (
        <EventDetailModal key={token + selected.id} id={selected.id} close={() => setSelected(null)} />
      )}
    </section>
  );
}
