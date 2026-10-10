'use client';
import { useState, useRef } from 'react';
import type { FormEvent } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { useRemote } from '@/hooks/useRemote';
import { eventsApi, resourcesApi } from '@/lib/api/endpoints';
import { errorMessage } from '@/lib/api/client';
import { toCampusISO, validateEventPlan } from '@/lib/campus-time';
import type { EventCreate, EventCreatedOut } from '@/types/core-api';
import ConflictSidebar from '@/components/ConflictSidebar';
import RemoteState from '@/components/RemoteState';
import { useToast } from '@/components/Toast';
import ProposalUpload from '@/components/ProposalUpload';

const input = 'mt-1 block w-full rounded-lg border border-stone-300 bg-white p-3';
export default function PlanPage() {
  const { token, activeClub } = useAuth();
  return <PlanForm key={token + ':' + activeClub?.club_id} />;
}
function PlanForm() {
  const { token, activeClub } = useAuth(); const { toast } = useToast();
  const [title, setTitle] = useState(''); const [description, setDescription] = useState('');
  const [date, setDate] = useState(''); const [endDate, setEndDate] = useState('');
  const [start, setStart] = useState(''); const [end, setEnd] = useState('');
  const [venue, setVenue] = useState(''); const [attendance, setAttendance] = useState('');
  const [saving, setSaving] = useState(false); const [error, setError] = useState('');
  const [created, setCreated] = useState<EventCreatedOut | null>(null);
  const pending = useRef<{ payload: string; key: string } | null>(null);
  const venues = useRemote(token, signal => resourcesApi.list(token!, { kind: 'VENUE', limit: 100 }, signal));
  let candidate: EventCreate | null = null; let validation = '';
  try {
    if (activeClub && date && start && end && title) {
      candidate = { club_id: activeClub.club_id, title: title.trim(), description: description.trim() || null, start_at: toCampusISO(date, start), end_at: toCampusISO(endDate || date, end), resource_id: venue || null, expected_attendance: attendance === '' ? null : Number(attendance), audience_tags: [] };
      validation = validateEventPlan(candidate) || '';
    }
  } catch (err) { validation = errorMessage(err); }
  const payload = candidate && !validation ? JSON.stringify(candidate) : null;
  const preview = useRemote(token && payload && !created ? token + payload : null, async signal => {
    await new Promise<void>((resolve, reject) => { const timer = setTimeout(resolve, 450); signal.addEventListener('abort', () => { clearTimeout(timer); reject(new DOMException('Aborted', 'AbortError')); }, { once: true }); });
    return eventsApi.preview(token!, JSON.parse(payload!), signal);
  });
  async function submit(event: FormEvent) {
    event.preventDefault(); if (!token || !candidate || validation || saving || created) return;
    const body = JSON.stringify(candidate);
    if (pending.current?.payload !== body) pending.current = { payload: body, key: crypto.randomUUID() };
    setSaving(true); setError('');
    try { const result = await eventsApi.create(token, candidate, pending.current.key); setCreated(result); toast('success', 'Event draft saved', 'A draft is not a booking.'); }
    catch (err) { setError(errorMessage(err)); }
    finally { setSaving(false); }
  }
  return <section className="mx-auto max-w-6xl p-4 md:p-8"><h1 className="text-3xl font-bold text-[#7a1b32]">Plan an event</h1><p className="my-3">Save a tentative draft for {activeClub?.club_name ?? 'your selected club'}. Times use Asia/Kolkata.</p>
    {!token ? <RemoteState signedIn={false} loading={false} retry={() => {}} /> : !activeClub ? <p>No club membership is available for this session.</p> : <>
      <div className="grid gap-6 lg:grid-cols-[1fr_360px]"><form onSubmit={submit} className="space-y-4 rounded-2xl border bg-white p-5">
        <fieldset disabled={saving || Boolean(created)} className="space-y-4">
          <label className="block">Event title<input required maxLength={200} value={title} onChange={e => setTitle(e.target.value)} className={input} /></label>
          <label className="block">Description<textarea value={description} onChange={e => setDescription(e.target.value)} className={input} /></label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label>Start date<input type="date" required value={date} onChange={e => setDate(e.target.value)} className={input} /></label>
            <label>Start time<input type="time" required value={start} onChange={e => setStart(e.target.value)} className={input} /></label>
            <label>End date<input type="date" value={endDate || date} onChange={e => setEndDate(e.target.value)} className={input} /></label>
            <label>End time<input type="time" required value={end} onChange={e => setEnd(e.target.value)} className={input} /></label>
          </div>
          <label className="block">Venue<select value={venue} onChange={e => setVenue(e.target.value)} className={input}><option value="">Unspecified — availability unknown</option>{venues.data?.items.map(v => <option key={v.id} value={v.id}>{v.name} · {v.availability_state}{v.synthetic ? ' · Synthetic demo' : ''}</option>)}</select></label>
          <RemoteState signedIn={Boolean(token)} {...venues} />
          {venues.data && venues.data.total > venues.data.items.length && <p className="text-xs">Showing the first 100 venues. Find additional resources in the venue explorer.</p>}
          <label className="block">Expected attendance<input type="number" min="0" step="1" value={attendance} onChange={e => setAttendance(e.target.value)} className={input} /></label>
          {validation && <p role="alert" className="text-rose-800">{validation}</p>}
          <button disabled={!payload || saving} className="rounded-xl bg-[#7a1b32] px-5 py-3 text-white disabled:opacity-50">{saving ? 'Saving…' : 'Save event draft'}</button>
        </fieldset>
        {error && <p role="alert" className="text-rose-800">{error}</p>}
        {created && <div role="status"><p>Saved {created.event.title} · {created.event.status}</p><Link className="underline" href={'/changes?eventId=' + created.event.id}>Open event and review next steps</Link></div>}
      </form><ConflictSidebar result={created ? { event_id: created.event.id, evaluated_as: created.event.status, has_blocking: created.conflicts.some(c => c.severity === 'blocking'), conflicts: created.conflicts, checked_at: created.event.created_at } : preview.data} loading={preview.loading} error={preview.error} /></div>
      {created && <ProposalUpload key={token + created.event.id} eventId={created.event.id} clubId={created.event.club_id} />}
    </>}
  </section>;
}
