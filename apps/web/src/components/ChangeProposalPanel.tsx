'use client';
import { useRef, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRemote } from '@/hooks/useRemote';
import { changesApi, resourcesApi } from '@/lib/api/endpoints';
import { errorMessage } from '@/lib/api/client';
import { fromCampusISO, toCampusISO } from '@/lib/campus-time';
import type { ChangeFields, DependencyCreate, EventOut, ImpactItem } from '@/types/core-api';
import RemoteState from './RemoteState';

const fields = ['start_at', 'end_at', 'resource_id', 'expected_attendance'] as const;

function Impact({ items }: { items: ImpactItem[] }) {
  return items.length ? <ul className="space-y-2">{items.map(item => <li key={item.dependent_id} className="rounded border p-3"><strong>{item.title}</strong><p>{item.reason}</p><p>{item.revalidation_required ? 'Requires revalidation' : 'Draft only'}</p></li>)}</ul> : <p>No registered dependencies match these changes. Review other commitments with your team.</p>;
}

export default function ChangeProposalPanel({ event, refresh }: { event: EventOut; refresh: () => void }) {
  const { token, session } = useAuth();
  const membership = session?.user.memberships?.find(item => item.club_id === event.club_id);
  const canEdit = Boolean(session?.user.campus_admin || membership);
  const canApply = Boolean(session?.user.campus_admin || membership?.role === 'CLUB_ADMIN');
  const terminal = ['COMPLETED', 'CANCELLED', 'REJECTED'].includes(event.status);
  const begin = fromCampusISO(event.start_at), finish = fromCampusISO(event.end_at);
  const [start, setStart] = useState(begin.date + 'T' + begin.time);
  const [end, setEnd] = useState(finish.date + 'T' + finish.time);
  const [venue, setVenue] = useState(event.resource_id ?? '');
  const [attendance, setAttendance] = useState(event.expected_attendance?.toString() ?? '');
  const [reason, setReason] = useState('');
  const [title, setTitle] = useState('');
  const [kind, setKind] = useState<DependencyCreate['kind']>('TASK');
  const [bindings, setBindings] = useState<DependencyCreate['field_paths']>(['start_at']);
  const [offset, setOffset] = useState(0);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  const [notice, setNotice] = useState('');
  const keys = useRef(new Map<string, string>());
  const key = token && canEdit ? token + event.id : null;
  const dependencies = useRemote(key, signal => changesApi.dependencies(token!, event.id, signal));
  const proposals = useRemote(key && key + offset, signal => changesApi.list(token!, event.id, offset, signal));
  const venues = useRemote(key, signal => resourcesApi.list(token!, { kind: 'VENUE', limit: 100 }, signal));
  let changes: ChangeFields = {}, validation = '';
  try {
    const [day, time] = start.split('T'), [lastDay, lastTime] = end.split('T');
    const startAt = start === begin.date + 'T' + begin.time ? event.start_at : toCampusISO(day, time);
    const endAt = end === finish.date + 'T' + finish.time ? event.end_at : toCampusISO(lastDay, lastTime);
    if (Date.parse(startAt) >= Date.parse(endAt)) throw new Error('End must be after start.');
    if (Date.parse(startAt) !== Date.parse(event.start_at)) changes.start_at = startAt;
    if (Date.parse(endAt) !== Date.parse(event.end_at)) changes.end_at = endAt;
    if ((venue || null) !== event.resource_id) changes.resource_id = venue || null;
    const count = attendance === '' ? null : Number(attendance);
    if (count !== null && (!Number.isInteger(count) || count < 0)) throw new Error('Attendance must be a non-negative whole number.');
    if (count !== event.expected_attendance) changes.expected_attendance = count;
  } catch (error) { validation = errorMessage(error); changes = {}; }
  const payload = !validation && Object.keys(changes).length ? JSON.stringify({ expected_revision: event.revision, changes }) : null;
  const preview = useRemote(key && payload && !terminal ? key + payload + dependencies.data?.total : null, signal => changesApi.preview(token!, event.id, JSON.parse(payload!), signal));
  function retryKey(signature: string) {
    if (!keys.current.has(signature)) keys.current.set(signature, crypto.randomUUID());
    return keys.current.get(signature)!;
  }
  async function mutate(action: () => Promise<unknown>, message: string, applied = false) {
    if (busy) return;
    setBusy(true); setFailure(''); setNotice('');
    try { await action(); setNotice(message); dependencies.retry(); proposals.retry(); preview.retry(); if (applied) refresh(); }
    catch (error) { setFailure(errorMessage(error)); }
    finally { setBusy(false); }
  }
  if (!canEdit) return <p>Change proposals and dependencies are available to this event&apos;s club and campus administrators.</p>;
  return <section className="space-y-4 border-t pt-4" aria-label="Schedule changes and dependencies">
    <h3 className="text-xl font-bold">Staged changes and dependency impact</h3>
    <p className="text-sm">Staging saves a proposal without changing the event. An administrator applies it after review. Schedule or venue changes to a confirmed event return it to submitted status.</p>
    <fieldset disabled={busy || terminal} className="grid gap-3 sm:grid-cols-2">
      <legend className="font-bold">Propose a recorded change</legend>
      <label>Change start (Asia/Kolkata)<input className="block w-full rounded border p-2" type="datetime-local" value={start} onChange={e => setStart(e.target.value)} /></label>
      <label>Change end (Asia/Kolkata)<input className="block w-full rounded border p-2" type="datetime-local" value={end} onChange={e => setEnd(e.target.value)} /></label>
      <label>Change venue<select className="block w-full rounded border p-2" value={venue} onChange={e => setVenue(e.target.value)}><option value="">Unspecified</option>{venue && !venues.data?.items.some(item => item.id === venue) && <option value={venue}>Current venue</option>}{venues.data?.items.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <label>Change attendance estimate<input className="block w-full rounded border p-2" type="number" min="0" step="1" value={attendance} onChange={e => setAttendance(e.target.value)} /></label>
      <label className="sm:col-span-2">Change reason<textarea className="block w-full rounded border p-2" maxLength={500} value={reason} onChange={e => setReason(e.target.value)} /></label>
      <button className="rounded border px-4 py-2 disabled:opacity-50" disabled={!payload || !reason.trim() || !preview.data} onClick={() => {
        const request = { ...JSON.parse(payload!), reason: reason.trim() };
        void mutate(() => changesApi.stage(token!, event.id, request, retryKey('stage' + JSON.stringify(request))), 'Change proposal saved. The event is unchanged.');
      }}>Stage change proposal</button>
    </fieldset>
    {terminal && <p>This event is closed to changes.</p>}
    {validation && <p role="alert">{validation}</p>}
    <RemoteState signedIn={Boolean(token)} {...venues} />
    {payload && !terminal && <div className="space-y-3"><RemoteState signedIn={Boolean(token)} {...preview} />{preview.data && <><p>Advisory preview as {preview.data.evaluated_as}; Core checks again when applying.</p><Impact items={preview.data.impact} />{preview.data.conflicts.map((item, index) => <p key={index}>{item.type}: {item.message}</p>)}</>}</div>}
    <fieldset disabled={busy || terminal} className="space-y-3 border-t pt-3">
      <legend className="font-bold">Register a dependency</legend>
      <p className="text-sm">Record organizer-reported work that depends on these fields. This does not confirm approval or book a venue.</p>
      <label className="block">Dependency title<input className="ml-2 max-w-full rounded border p-2" maxLength={200} value={title} onChange={e => setTitle(e.target.value)} /></label>
      <label className="block">Dependency kind<select className="ml-2 rounded border p-2" value={kind} onChange={e => setKind(e.target.value as DependencyCreate['kind'])}><option value="TASK">Task</option><option value="COMMITMENT">Requested commitment</option></select></label>
      <div className="flex flex-wrap gap-3">{fields.map(field => <label key={field}><input type="checkbox" checked={bindings.includes(field)} onChange={e => setBindings(e.target.checked ? [...bindings, field] : bindings.filter(item => item !== field))} /> Depends on {field.replaceAll('_', ' ')}</label>)}</div>
      <button className="rounded border px-4 py-2 disabled:opacity-50" disabled={!title.trim() || !bindings.length} onClick={() => {
        const request = { kind, title: title.trim(), field_paths: [...bindings].sort() };
        void mutate(() => changesApi.register(token!, event.id, request, retryKey('dependency' + JSON.stringify(request))), 'Dependency recorded.');
      }}>Record dependency</button>
    </fieldset>
    <RemoteState signedIn={Boolean(token)} {...dependencies} />
    <ul className="space-y-2">{dependencies.data?.items.map(item => <li key={item.id} className="rounded border p-3">{item.title} · {item.status}{item.needs_revalidation ? ' · Needs revalidation' : ''}<p className="text-sm">Depends on {item.field_paths.join(', ')}</p></li>)}</ul>
    <h4 className="font-bold">Saved change proposals</h4>
    <RemoteState signedIn={Boolean(token)} {...proposals} />
    {proposals.data?.items.map(item => <article key={item.id} className="space-y-2 rounded border p-3"><h5 className="font-bold">{item.reason} · {item.status}</h5><p>Based on revision {item.base_revision}</p><pre className="overflow-auto whitespace-pre-wrap text-sm">{JSON.stringify(item.changes, null, 2)}</pre><Impact items={item.impact} />
      {item.status === 'STAGED' && (canApply ? <button className="rounded border px-4 py-2 disabled:opacity-50" disabled={busy || terminal || item.base_revision !== event.revision} onClick={() => void mutate(() => changesApi.apply(token!, event.id, item.id, { expected_revision: item.base_revision }, retryKey('apply' + item.id)), 'Change applied.', true)}>Apply staged change</button> : <p>An administrator must apply this change.</p>)}
      {item.status === 'STAGED' && item.base_revision !== event.revision && <p>This proposal is stale. Reload the event and stage a new proposal.</p>}
    </article>)}
    {proposals.data && <div className="flex gap-4"><button disabled={busy || !offset} onClick={() => setOffset(Math.max(0, offset - 20))}>Previous changes</button><button disabled={busy || offset + 20 >= proposals.data.total} onClick={() => setOffset(offset + 20)}>More changes</button></div>}
    {notice && <p role="status">{notice}</p>}{failure && <div role="alert"><p>{failure}</p><button className="underline" onClick={refresh}>Reload current event</button></div>}
  </section>;
}
