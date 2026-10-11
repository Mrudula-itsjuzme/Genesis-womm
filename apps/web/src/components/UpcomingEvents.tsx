'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { useRemote } from '@/hooks/useRemote';
import { eventsApi } from '@/lib/api/endpoints';
import { campusFormat } from '@/lib/campus-time';
import RemoteState from './RemoteState';
import { Calendar, Clock, ChevronRight, ChevronLeft, ArrowUpRight } from 'lucide-react';

function getStatusBadge(status: string) {
  switch (status) {
    case 'CONFIRMED':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200/80';
    case 'PROPOSED':
      return 'bg-blue-50 text-blue-700 border-blue-200/80';
    case 'ACKNOWLEDGED':
      return 'bg-indigo-50 text-indigo-700 border-indigo-200/80';
    case 'CANCELLED':
      return 'bg-rose-50 text-rose-700 border-rose-200/80';
    case 'DRAFT':
    default:
      return 'bg-amber-50 text-amber-700 border-amber-200/80';
  }
}


export default function UpcomingEvents() {
  const { token, activeClub } = useAuth();
  return <UpcomingList key={token + ':' + activeClub?.club_id} />;
}

function UpcomingList() {
  const { token, activeClub } = useAuth();
  const [offset, setOffset] = useState(0);
  const remote = useRemote(
    token && token + activeClub?.club_id + offset,
    signal => eventsApi.list(token!, { club_id: activeClub?.club_id, limit: 6, offset }, signal)
  );

  return (
    <section className="rounded-[10px] border border-stone-200/80 bg-white/95 p-5 shadow-sm backdrop-blur-xl">
      <RemoteState signedIn={Boolean(token)} {...remote} empty={remote.data?.items.length === 0} />

      <div className="space-y-2.5">
        {remote.data?.items.map(event => (
          <article
            key={event.id}
            className="group relative rounded-[10px] border border-stone-200/70 bg-white p-3.5 shadow-2xs transition-all duration-150 ease-out hover:border-[#7a1b32]/40 hover:shadow-sm active:scale-[0.99]"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5 mb-1.5">
                  <span
                    className={`inline-flex items-center rounded-[6px] border px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase ${getStatusBadge(
                      event.status
                    )}`}
                  >
                    {event.status}
                  </span>
                </div>

                <Link
                  href={'/changes?eventId=' + event.id}
                  className="block font-semibold text-stone-900 group-hover:text-[#7a1b32] transition-colors text-sm tracking-tight truncate"
                >
                  {event.title}
                </Link>

                <div className="mt-1.5 flex flex-wrap items-center gap-3 text-xs text-stone-500">
                  <span className="inline-flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-stone-400" />
                    {campusFormat(event.start_at, { dateStyle: 'medium' })}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-stone-400" />
                    {campusFormat(event.start_at, { timeStyle: 'short' })} –{' '}
                    {campusFormat(event.end_at, { timeStyle: 'short' })}
                  </span>
                </div>
              </div>

              <Link
                href={'/changes?eventId=' + event.id}
                className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[8px] border border-stone-200 bg-stone-50 text-stone-500 transition-all duration-150 group-hover:border-[#7a1b32]/30 group-hover:bg-rose-50 group-hover:text-[#7a1b32] active:scale-95"
                aria-label={'View details for ' + event.title}
              >
                <ArrowUpRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </Link>
            </div>
          </article>
        ))}
      </div>

      {remote.data && (
        <div className="mt-4 flex items-center justify-between border-t border-stone-100 pt-3">
          <button
            disabled={!offset}
            onClick={() => setOffset(Math.max(0, offset - 6))}
            className="inline-flex items-center gap-1 rounded-[8px] border border-stone-300/80 bg-white px-3 py-1.5 text-xs font-semibold text-stone-700 shadow-2xs transition-all hover:bg-stone-50 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ChevronLeft className="w-3.5 h-3.5" /> Previous
          </button>
          <span className="text-xs font-medium text-stone-500">
            {remote.data.total > 0
              ? `Showing ${offset + 1}–${Math.min(offset + 6, remote.data.total)} of ${remote.data.total} events`
              : '0 events'}
          </span>
          <button
            disabled={offset + 6 >= remote.data.total}
            onClick={() => setOffset(offset + 6)}
            className="inline-flex items-center gap-1 rounded-[8px] border border-stone-300/80 bg-white px-3 py-1.5 text-xs font-semibold text-stone-700 shadow-2xs transition-all hover:bg-stone-50 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
          >
            Next <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </section>
  );
}
