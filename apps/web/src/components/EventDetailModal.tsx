'use client';
import { useEffect, useRef } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { useRemote } from '@/hooks/useRemote';
import { eventsApi, resourcesApi } from '@/lib/api/endpoints';
import { campusFormat } from '@/lib/campus-time';
import RemoteState from './RemoteState';

export default function EventDetailModal({ id, close }: { id: string; close: () => void }) {
  const { token } = useAuth(); const dialog = useRef<HTMLDialogElement>(null);
  const event = useRemote(token && token + id, signal => eventsApi.get(token!, id, signal));
  const venue = useRemote(token && event.data?.resource_id ? token + event.data.resource_id : null, () => resourcesApi.get(token!, event.data!.resource_id!));
  useEffect(() => { const element = dialog.current; element?.showModal(); return () => element?.close(); }, []);
  return <dialog ref={dialog} onCancel={close} aria-labelledby="event-detail-title" className="m-auto w-[min(38rem,calc(100vw-2rem))] rounded-2xl p-6 backdrop:bg-black/40"><button className="float-right rounded border px-3 py-1" onClick={close} aria-label="Close event details">×</button><h2 id="event-detail-title" className="mb-4 text-xl font-bold">Event details</h2><RemoteState signedIn={Boolean(token)} {...event} />
    {event.data && <div className="space-y-3"><h3 className="text-2xl font-bold">{event.data.title}</h3><p>{event.data.description}</p><p>{event.data.status} · Revision {event.data.revision}{event.data.synthetic ? ' · Synthetic demo' : ''}</p><p>{campusFormat(event.data.start_at)} – {campusFormat(event.data.end_at)}</p><p>Venue: {venue.data?.name ?? (event.data.resource_id ? 'Loading recorded resource…' : 'Unspecified')}</p>{venue.error && <RemoteState signedIn={Boolean(token)} {...venue} />}<p>Venue availability: {event.data.venue_availability}</p><p>Expected attendance: {event.data.expected_attendance ?? 'Not recorded'}</p><p className="text-sm">A tentative proposal is not a booking. Acknowledgments and official confirmations are separate.</p><Link className="inline-block underline" href={'/changes?eventId=' + id}>Review schedule, evidence, and status actions</Link></div>}
  </dialog>;
}
