'use client';
import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRemote } from '@/hooks/useRemote';
import { eventsApi, resourcesApi } from '@/lib/api/endpoints';
import { ApiResponseError, errorMessage } from '@/lib/api/client';
import { fromCampusISO, toCampusISO, campusFormat, validateEventPlan } from '@/lib/campus-time';
import { allowedTransitions } from '@/lib/lifecycle';
import type { EventOut, EventStatus } from '@/types/core-api';
import ConflictSidebar from './ConflictSidebar';
import RemoteState from './RemoteState';
import ProposalUpload from './ProposalUpload';
import ChangeProposalPanel from './ChangeProposalPanel';

export default function ChangeImpactList({ initialEventId }: { initialEventId?: string }) {
  const { token } = useAuth();
  return <EventSelector key={token} initialEventId={initialEventId} />;
}
function EventSelector({ initialEventId }: { initialEventId?: string }) {
  const { token } = useAuth(); const [id, setId] = useState(initialEventId ?? ''); const [offset, setOffset] = useState(0);
  const list = useRemote(token && token + offset, signal => eventsApi.list(token!, { limit: 50, offset }, signal));
  const selected = useRemote(token && id ? token + id : null, signal => eventsApi.get(token!, id, signal));
  return <div className="space-y-5"><label className="block">Event<select className="ml-3 max-w-full rounded-lg border bg-white p-3" value={id} onChange={e => setId(e.target.value)}><option value="">Select an event</option>{id && !list.data?.items.some(e => e.id === id) && <option value={id}>Selected event</option>}{list.data?.items.map(e => <option key={e.id} value={e.id}>{e.title} · {e.status}</option>)}</select></label>
    <RemoteState signedIn={Boolean(token)} {...list} empty={list.data?.total === 0} />
    {list.data && <div className="flex gap-4"><button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 50))}>Previous events</button><button disabled={offset + 50 >= list.data.total} onClick={() => setOffset(offset + 50)}>More events</button></div>}
    {id && <RemoteState signedIn={Boolean(token)} {...selected} />}
    {selected.data && <EventWorkspace key={token + selected.data.id + selected.data.revision} event={selected.data} refresh={selected.retry} />}
  </div>;
}
function EventWorkspace({ event, refresh }: { event: EventOut; refresh: () => void }) {
  const { token, session } = useAuth();
  const begin = fromCampusISO(event.start_at), finish = fromCampusISO(event.end_at);
  const [date, setDate] = useState(begin.date); const [start, setStart] = useState(begin.time);
  const [endDate, setEndDate] = useState(finish.date); const [end, setEnd] = useState(finish.time);
  const [venue, setVenue] = useState(event.resource_id ?? '');
  const [kind, setKind] = useState(''); const [reference, setReference] = useState(''); const [captured, setCaptured] = useState('');
  const [busy, setBusy] = useState(false); const [failure, setFailure] = useState<{ message: string; details?: unknown[] } | null>(null);
  const venues = useRemote(token, signal => resourcesApi.list(token!, { kind: 'VENUE', limit: 100 }, signal));
  let candidate: { start_at: string; end_at: string; resource_id: string | null; as_status: 'CONFIRMED' } | null = null; let validation = '';
  try { candidate = { start_at: toCampusISO(date, start), end_at: toCampusISO(endDate, end), resource_id: venue || null, as_status: 'CONFIRMED' }; validation = validateEventPlan({ ...candidate, title: event.title }) || ''; }
  catch (err) { validation = errorMessage(err); }
  const payload = candidate && !validation ? JSON.stringify(candidate) : null;
  const preview = useRemote(token && payload ? token + event.id + event.revision + payload : null, signal => eventsApi.checkConflicts(token!, event.id, JSON.parse(payload!), signal));
  const actions = session ? allowedTransitions(event.status, event.club_id, session.user) : [];
  async function transition(target: EventStatus) {
    if (!token || busy) return;
    setBusy(true); setFailure(null);
    try {
      let evidence;
      if (target === 'CONFIRMED') {
        if (!kind.trim() || !reference.trim() || !captured) throw new Error('Provide evidence kind, reference, and capture date/time for confirmation.');
        const [day, time] = captured.split('T');
        evidence = { kind: kind.trim(), reference: reference.trim(), captured_at: toCampusISO(day, time) };
      }
      await eventsApi.transition(token, event.id, { target_status: target, expected_revision: event.revision, ...(evidence ? { evidence } : {}) });
      refresh();
    } catch (err) { setFailure({ message: errorMessage(err), details: err instanceof ApiResponseError ? err.details : undefined }); }
    finally { setBusy(false); }
  }
  return <div className="grid gap-6 lg:grid-cols-[1fr_360px]"><section className="space-y-5 rounded-2xl border bg-white p-5">
    <div><h2 className="text-2xl font-bold">{event.title}</h2><p>{event.description}</p><p>{event.status} · Revision {event.revision}{event.synthetic ? ' · Synthetic demo' : ''}</p><p>{campusFormat(event.start_at)} – {campusFormat(event.end_at)}</p><p>Venue availability: {event.venue_availability}</p></div>
    <section><h3 className="text-lg font-bold">Preview confirmation conflicts</h3><p className="my-2 text-sm">Advisory preview as CONFIRMED. Use the staged change form below to save and review a change.</p>
      <div className="grid gap-3 sm:grid-cols-2"><label>Proposed start date<input className="block w-full rounded border p-2" type="date" value={date} onChange={e => setDate(e.target.value)} /></label><label>Proposed start time<input className="block w-full rounded border p-2" type="time" value={start} onChange={e => setStart(e.target.value)} /></label><label>Proposed end date<input className="block w-full rounded border p-2" type="date" value={endDate} onChange={e => setEndDate(e.target.value)} /></label><label>Proposed end time<input className="block w-full rounded border p-2" type="time" value={end} onChange={e => setEnd(e.target.value)} /></label></div>
      <label className="my-3 block">Proposed venue<select className="ml-2 max-w-full rounded border p-2" value={venue} onChange={e => setVenue(e.target.value)}><option value="">Unspecified</option>{venue && !venues.data?.items.some(v => v.id === venue) && <option value={venue}>Current venue ({venue})</option>}{venues.data?.items.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}</select></label><RemoteState signedIn={Boolean(token)} {...venues} />{validation && <p role="alert">{validation}</p>}
    </section>
    <section className="border-t pt-4"><h3 className="font-bold">Change recorded status</h3><p className="my-2 text-sm">Applies to the recorded schedule above. Core checks permissions, revision, evidence, and conflicts again.</p>
      {actions.includes('CONFIRMED') && <fieldset disabled={busy} className="space-y-2"><legend>Confirmation evidence</legend><label className="block">Evidence kind<input className="ml-2 rounded border p-2" value={kind} onChange={e => setKind(e.target.value)} /></label><label className="block">Evidence reference<input className="ml-2 rounded border p-2" value={reference} onChange={e => setReference(e.target.value)} /></label><label className="block">Captured at (Asia/Kolkata)<input type="datetime-local" className="ml-2 rounded border p-2" value={captured} onChange={e => setCaptured(e.target.value)} /></label></fieldset>}
      <div className="my-3 flex flex-wrap gap-2">{actions.map(target => <button disabled={busy} key={target} onClick={() => transition(target)} className="rounded-lg border bg-rose-50 px-4 py-2 disabled:opacity-50">Mark {target.toLowerCase()}</button>)}</div>{!actions.length && <p>No status changes are available for this session and event.</p>}
      {failure && <div role="alert"><p>{failure.message}</p>{Boolean(failure.details?.length) && <details><summary>Core validation details</summary><pre className="max-w-full overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(failure.details, null, 2)}</pre></details>}<button className="mt-2 underline" onClick={refresh}>Reload current event</button></div>}
    </section>
    <ProposalUpload key={token + event.id} eventId={event.id} clubId={event.club_id} />
    <ChangeProposalPanel event={event} refresh={refresh} />
  </section><ConflictSidebar {...preview} result={preview.data} error={preview.error} /></div>;
}
