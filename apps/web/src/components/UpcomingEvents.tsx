'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { useRemote } from '@/hooks/useRemote';
import { eventsApi } from '@/lib/api/endpoints';
import { campusFormat } from '@/lib/campus-time';
import RemoteState from './RemoteState';
export default function UpcomingEvents() {
  const { token, activeClub } = useAuth();
  return <UpcomingList key={token + ':' + activeClub?.club_id} />;
}
function UpcomingList() {
  const { token, activeClub } = useAuth(); const [offset, setOffset] = useState(0);
  const remote = useRemote(token && token + activeClub?.club_id + offset, signal => eventsApi.list(token!, { club_id: activeClub?.club_id, limit: 6, offset }, signal));
  return <section className="rounded-2xl border bg-white p-5"><div className="mb-4 flex justify-between"><h2 className="text-xl font-bold">{activeClub?.club_name ?? 'Campus'} events</h2><Link className="underline" href="/calendar">Calendar</Link></div><RemoteState signedIn={Boolean(token)} {...remote} empty={remote.data?.items.length === 0} /><div className="space-y-3">{remote.data?.items.map(event => <article key={event.id} className="rounded-xl border p-4"><Link className="font-bold underline" href={'/changes?eventId=' + event.id}>{event.title}</Link><p className="my-1 text-sm">{campusFormat(event.start_at)} – {campusFormat(event.end_at)}</p><p className="text-xs">{event.status} · Venue availability: {event.venue_availability}{event.synthetic ? ' · Synthetic demo' : ''}</p></article>)}</div>{remote.data && <div className="mt-4 flex gap-3"><button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 6))}>Previous</button><span>{remote.data.total} events</span><button disabled={offset + 6 >= remote.data.total} onClick={() => setOffset(offset + 6)}>Next</button></div>}</section>;
}
