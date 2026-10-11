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

const input = 'mt-1 block w-full rounded-[10px] border border-stone-300/80 bg-white p-2.5 text-sm transition-all focus:border-[#7a1b32] focus:outline-none focus:ring-2 focus:ring-[#7a1b32]/15';
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
  return <section className="mx-auto max-w-6xl p-4 md:p-8"><h1 className="text-3xl font-bold tracking-tight text-[#7a1b32]">Plan an event</h1><p className="my-3 text-sm text-stone-600">Save a tentative draft for {activeClub?.club_name ?? 'your selected club'}. Times use Asia/Kolkata.</p>
    {!token ? <RemoteState signedIn={false} loading={false} retry={() => {}} /> : !activeClub ? (
      <div className="rounded-[10px] border border-amber-200/80 bg-amber-50/90 p-6 text-amber-900 shadow-sm backdrop-blur-md">
        <div className="flex items-center gap-2 font-semibold">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-purple-600 shadow-[0_0_6px_rgba(147,51,234,0.5)]"></span>
          <span>Campus Administrator Mode</span>
        </div>
        <p className="mt-2 text-sm text-amber-800">
          Administrative accounts do not hold direct club memberships. To review submitted drafts, resolve conflicts, and grant official confirmations, visit the review workspace.
        </p>
        <Link
          href="/changes"
          className="mt-4 inline-block rounded-[10px] bg-[#7a1b32] px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all duration-150 ease-out hover:bg-[#631628] active:scale-[0.98]"
        >
          Go to Event Approvals & Changes →
        </Link>
      </div>
    ) : <>
      <div className="grid gap-6 lg:grid-cols-[1fr_360px]"><form onSubmit={submit} className="space-y-4 rounded-[10px] border border-stone-200/80 bg-white/95 p-6 shadow-sm backdrop-blur-xl">
        <fieldset disabled={saving || Boolean(created)} className="space-y-4">
          <label className="block text-sm font-medium text-stone-700">Event title<input required maxLength={200} value={title} onChange={e => setTitle(e.target.value)} className={input} /></label>
          <label className="block text-sm font-medium text-stone-700">Description<textarea value={description} onChange={e => setDescription(e.target.value)} className={input} /></label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium text-stone-700">Start date<input type="date" required value={date} onChange={e => setDate(e.target.value)} className={input} /></label>
            <label className="text-sm font-medium text-stone-700">Start time<input type="time" required value={start} onChange={e => setStart(e.target.value)} className={input} /></label>
            <label className="text-sm font-medium text-stone-700">End date<input type="date" value={endDate || date} onChange={e => setEndDate(e.target.value)} className={input} /></label>
            <label className="text-sm font-medium text-stone-700">End time<input type="time" required value={end} onChange={e => setEnd(e.target.value)} className={input} /></label>
          </div>
          <label className="block text-sm font-medium text-stone-700">Venue<select value={venue} onChange={e => setVenue(e.target.value)} className={input}><option value="">Unspecified — availability unknown</option>{venues.data?.items.map(v => <option key={v.id} value={v.id}>{v.name} · {v.availability_state}{v.synthetic ? ' · Synthetic demo' : ''}</option>)}</select></label>
          <RemoteState signedIn={Boolean(token)} {...venues} />
          {venues.data && venues.data.total > venues.data.items.length && <p className="text-xs text-stone-500">Showing the first 100 venues. Find additional resources in the venue explorer.</p>}
          <label className="block text-sm font-medium text-stone-700">Expected attendance<input type="number" min="0" step="1" value={attendance} onChange={e => setAttendance(e.target.value)} className={input} /></label>
          {validation && <p role="alert" className="text-sm font-medium text-rose-800">{validation}</p>}
          <button disabled={!payload || saving} className="rounded-[10px] bg-[#7a1b32] px-5 py-3 text-sm font-semibold text-white shadow-sm transition-all duration-150 ease-out hover:bg-[#631628] active:scale-[0.98] disabled:opacity-50">{saving ? 'Saving…' : 'Save event draft'}</button>
        </fieldset>
        {error && <p role="alert" className="text-sm font-medium text-rose-800">{error}</p>}
        {created && <div role="status" className="rounded-[10px] border border-emerald-200 bg-emerald-50/80 p-4 text-sm text-emerald-900"><p className="font-semibold">Saved {created.event.title} · {created.event.status}</p><Link className="mt-1 inline-block text-xs font-semibold text-[#7a1b32] underline" href={'/changes?eventId=' + created.event.id}>Open event and review next steps</Link></div>}
      </form><ConflictSidebar result={created ? { event_id: created.event.id, evaluated_as: created.event.status, has_blocking: created.conflicts.some(c => c.severity === 'blocking'), conflicts: created.conflicts, checked_at: created.event.created_at } : preview.data} loading={preview.loading} error={preview.error} /></div>
      {created && <ProposalUpload key={token + created.event.id} eventId={created.event.id} clubId={created.event.club_id} />}
    </>}
  </section>;
}
