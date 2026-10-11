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
  const { token, session, activeClub } = useAuth(); const [id, setId] = useState(initialEventId ?? ''); const [offset, setOffset] = useState(0);
  const list = useRemote(token && token + offset, signal => eventsApi.list(token!, { limit: 50, offset }, signal));
  const selected = useRemote(token && id ? token + id : null, signal => eventsApi.get(token!, id, signal));
  return <div className="space-y-5">
    {session && (
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-[10px] border border-stone-200/80 bg-white/95 p-3.5 shadow-sm backdrop-blur-xl">
        <div className="flex items-center gap-2 text-xs">
          <span className={"inline-block h-2.5 w-2.5 rounded-full " + (session.user.campus_admin ? "bg-purple-600 shadow-[0_0_6px_rgba(147,51,234,0.5)]" : "bg-emerald-600 shadow-[0_0_6px_rgba(5,150,105,0.5)]")} />
          <span className="font-semibold text-stone-700">Active Role:</span>
          <span className="rounded-[6px] bg-stone-100 px-2 py-0.5 font-medium text-stone-800">
            {session.user.campus_admin ? 'Campus Administrator · Institutional Approvals & Overrides' : `${activeClub?.club_name ?? 'Club Organizer'} · Event Proposals & Drafts`}
          </span>
        </div>
        {session.user.campus_admin && (
          <span className="rounded-[6px] bg-purple-50 px-2.5 py-1 text-[11px] font-semibold text-purple-700 border border-purple-200 shadow-xs">
            Authorized to confirm or reject proposals
          </span>
        )}
      </div>
    )}
    <label className="block text-sm font-medium text-stone-700">Event<select className="mt-1 w-full rounded-[10px] border border-stone-300/80 bg-white p-3 text-sm transition-all focus:border-[#7a1b32] focus:outline-none focus:ring-2 focus:ring-[#7a1b32]/15" value={id} onChange={e => setId(e.target.value)}><option value="">Select an event</option>{id && !list.data?.items.some(e => e.id === id) && <option value={id}>Selected event</option>}{list.data?.items.map(e => <option key={e.id} value={e.id}>{e.title} · {e.status}</option>)}</select></label>
    <RemoteState signedIn={Boolean(token)} {...list} empty={list.data?.total === 0} />
    {list.data && <div className="flex gap-3"><button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 50))} className="rounded-[10px] border border-stone-300 bg-white px-4 py-2 text-xs font-semibold text-stone-700 shadow-xs transition-all hover:bg-stone-50 active:scale-[0.98] disabled:opacity-40">Previous events</button><button disabled={offset + 50 >= list.data.total} onClick={() => setOffset(offset + 50)}>More events</button></div>}
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
  return <div className="grid gap-6 lg:grid-cols-[1fr_360px]"><section className="space-y-5 rounded-[10px] border border-stone-200/80 bg-white/95 p-6 shadow-sm backdrop-blur-xl">
    <div className="rounded-[10px] border border-stone-200 bg-stone-50/70 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-2xl font-bold tracking-tight text-stone-900">{event.title}</h2>
        <span className="rounded-[6px] bg-[#7a1b32]/10 px-3 py-1 text-xs font-semibold text-[#7a1b32]">{event.status}</span>
      </div>
      <p className="mt-1 text-sm text-stone-600">{event.description ?? 'No description provided.'}</p>
      <div className="mt-3 flex flex-wrap gap-4 text-xs font-medium text-stone-600">
        <span>🕒 {campusFormat(event.start_at)} – {campusFormat(event.end_at)}</span>
        <span>📍 Venue availability: {event.venue_availability}</span>
        <span>🔢 Revision {event.revision}</span>
        {event.synthetic && <span className="text-amber-700 font-semibold">🧪 Synthetic demo</span>}
      </div>
    </div>
    <section><h3 className="text-lg font-bold tracking-tight text-stone-900">Preview confirmation conflicts</h3><p className="my-2 text-sm text-stone-600">Advisory preview as CONFIRMED. Use the staged change form below to save and review a change.</p>
      <div className="grid gap-3 sm:grid-cols-2"><label className="text-sm font-medium text-stone-700">Proposed start date<input className="mt-1 block w-full rounded-[10px] border border-stone-300/80 p-2 text-sm transition focus:border-[#7a1b32] focus:outline-none" type="date" value={date} onChange={e => setDate(e.target.value)} /></label><label className="text-sm font-medium text-stone-700">Proposed start time<input className="mt-1 block w-full rounded-[10px] border border-stone-300/80 p-2 text-sm transition focus:border-[#7a1b32] focus:outline-none" type="time" value={start} onChange={e => setStart(e.target.value)} /></label><label className="text-sm font-medium text-stone-700">Proposed end date<input className="mt-1 block w-full rounded-[10px] border border-stone-300/80 p-2 text-sm transition focus:border-[#7a1b32] focus:outline-none" type="date" value={endDate} onChange={e => setEndDate(e.target.value)} /></label><label className="text-sm font-medium text-stone-700">Proposed end time<input className="mt-1 block w-full rounded-[10px] border border-stone-300/80 p-2 text-sm transition focus:border-[#7a1b32] focus:outline-none" type="time" value={end} onChange={e => setEnd(e.target.value)} /></label></div>
      <label className="my-3 block text-sm font-medium text-stone-700">Proposed venue<select className="mt-1 w-full rounded-[10px] border border-stone-300/80 p-2 text-sm transition focus:border-[#7a1b32] focus:outline-none" value={venue} onChange={e => setVenue(e.target.value)}><option value="">Unspecified</option>{venue && !venues.data?.items.some(v => v.id === venue) && <option value={venue}>Current venue ({venue})</option>}{venues.data?.items.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}</select></label><RemoteState signedIn={Boolean(token)} {...venues} />{validation && <p role="alert" className="text-sm font-medium text-rose-800">{validation}</p>}
    </section>
    <section className="border-t border-stone-100 pt-4"><h3 className="font-bold text-stone-900">Change recorded status</h3><p className="my-2 text-sm text-stone-600">Applies to the recorded schedule above. Core checks permissions, revision, evidence, and conflicts again.</p>
      {actions.includes('CONFIRMED') && <fieldset disabled={busy} className="space-y-2 rounded-[10px] border border-stone-200 bg-stone-50/50 p-4"><legend className="text-xs font-semibold text-stone-700">Confirmation evidence</legend><label className="block text-xs font-medium text-stone-700">Evidence kind<input className="mt-1 block w-full rounded-[8px] border border-stone-300 p-2 text-xs" value={kind} onChange={e => setKind(e.target.value)} /></label><label className="block text-xs font-medium text-stone-700">Evidence reference<input className="mt-1 block w-full rounded-[8px] border border-stone-300 p-2 text-xs" value={reference} onChange={e => setReference(e.target.value)} /></label><label className="block text-xs font-medium text-stone-700">Captured at (Asia/Kolkata)<input type="datetime-local" className="mt-1 block w-full rounded-[8px] border border-stone-300 p-2 text-xs" value={captured} onChange={e => setCaptured(e.target.value)} /></label></fieldset>}
      <div className="my-3 flex flex-wrap gap-2">{actions.map(target => <button disabled={busy} key={target} onClick={() => transition(target)} className="rounded-[10px] border border-rose-200 bg-rose-50 px-4 py-2 text-xs font-semibold text-[#7a1b32] shadow-xs transition-all duration-150 hover:bg-rose-100 active:scale-[0.98] disabled:opacity-50">Mark {target.toLowerCase()}</button>)}</div>{!actions.length && <p className="text-xs text-stone-500">No status changes are available for this session and event.</p>}
      {failure && <div role="alert" className="rounded-[10px] border border-rose-200 bg-rose-50/80 p-3 text-xs text-rose-900"><p>{failure.message}</p>{Boolean(failure.details?.length) && <details className="mt-2"><summary className="cursor-pointer font-medium">Core validation details</summary><pre className="max-w-full overflow-auto whitespace-pre-wrap text-xs mt-1">{JSON.stringify(failure.details, null, 2)}</pre></details>}<button className="mt-2 text-xs font-semibold text-[#7a1b32] underline" onClick={refresh}>Reload current event</button></div>}
    </section>
    <ProposalUpload key={token + event.id} eventId={event.id} clubId={event.club_id} />
    <ChangeProposalPanel event={event} refresh={refresh} />
  </section><ConflictSidebar {...preview} result={preview.data} error={preview.error} /></div>;
}
