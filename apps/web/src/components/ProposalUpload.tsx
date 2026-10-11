'use client';
import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRemote } from '@/hooks/useRemote';
import { proposalsApi } from '@/lib/api/endpoints';
import { errorMessage } from '@/lib/api/client';
import { validateProposal } from '@/lib/proposal';
import type { ProposalUploadOut, ProposalOut, ProposalStatusPatch } from '@/types/core-api';

export default function ProposalUpload({ eventId, clubId }: { eventId: string; clubId: string }) {
  const { token, session } = useAuth();
  const [file, setFile] = useState<File | null>(null); const [title, setTitle] = useState('');
  const [record, setRecord] = useState<ProposalUploadOut | ProposalOut | null>(null);
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const [url, setUrl] = useState(''); const [note, setNote] = useState('');
  const [existingId, setExistingId] = useState('');
  const documents = useRemote(token ? `${token}:${eventId}` : null, signal => proposalsApi.listForEvent(token!, eventId, signal));
  const role = session?.user.memberships?.find(m => m.club_id === clubId)?.role;
  const canUpload = session?.user.campus_admin || role === 'ORGANIZER' || role === 'CLUB_ADMIN';
  async function load(event: FormEvent) {
    event.preventDefault(); if (!token || !existingId.trim() || busy) return;
    setBusy(true); setError(''); setUrl(''); setRecord(null);
    try {
      const proposal = await proposalsApi.get(token, existingId.trim());
      if (proposal.event_id !== eventId || proposal.club_id !== clubId) throw new Error('This proposal belongs to another event or club.');
      setRecord(proposal);
    } catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }
  async function upload(event: FormEvent) {
    event.preventDefault(); if (!token || !file || busy) return;
    const invalid = validateProposal(file); if (invalid) { setError(invalid); return; }
    setBusy(true); setError(''); setUrl('');
    try { setRecord(await proposalsApi.upload(token, clubId, eventId, file, title.trim())); setFile(null); documents.retry(); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }
  async function download() {
    if (!token || !record || busy) return; setBusy(true); setError(''); setUrl('');
    try { const result = await proposalsApi.getDownloadUrl(token, record.id); setUrl(result.download_url); }
    catch (err) { setError('The upload is saved, but a download link could not be generated. ' + errorMessage(err)); }
    finally { setBusy(false); }
  }
  async function review(action: ProposalStatusPatch['action']) {
    if (!token || !record || busy) return; setBusy(true); setError('');
    try { setRecord(await proposalsApi.review(token, record.id, { action, review_note: note.trim() || null })); documents.retry(); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }
  const isFacultyAdvisor = role === 'FACULTY_ADVISOR';
  const canReview = Boolean(session?.user.campus_admin || isFacultyAdvisor);
  const readyForThisReviewer = Boolean(record && (session?.user.campus_admin
    ? record.status === 'FACULTY_APPROVED'
    : isFacultyAdvisor && ['SUBMITTED', 'UNDER_REVIEW'].includes(record.status)));
  const nextReviewStep = record?.status === 'FACULTY_APPROVED'
    ? 'Faculty review complete. Awaiting campus-level document review.'
    : record?.status === 'SUBMITTED' || record?.status === 'UNDER_REVIEW'
      ? 'Awaiting club faculty advisor review.'
      : record ? `Document status: ${record.status}. This does not confirm the event.` : '';
  return <section className="mt-6 rounded-2xl border bg-white p-5"><h2 className="text-xl font-bold">Proposal document</h2><p className="my-2 text-sm">PDF only, up to 15 MiB. Uploading or approving this document does not confirm the event or book a venue.</p>
    <div className="my-3 space-y-2"><label className="block text-sm font-medium">Documents for this event<select className="mt-1 block w-full rounded border p-2" value={record?.id ?? ''} onChange={e => { const next = documents.data?.find(d => d.id === e.target.value); setRecord(next ?? null); setUrl(''); setError(''); }}><option value="">Select an uploaded document</option>{documents.data?.map(d => <option key={d.id} value={d.id}>Revision {d.revision} · {d.title} · {d.status}</option>)}</select></label>{documents.loading && <p className="text-xs text-stone-500">Loading documents…</p>}{documents.error && <p role="alert" className="text-xs text-rose-800">Could not load event documents. <button className="underline" type="button" onClick={documents.retry}>Retry</button></p>}{documents.data?.length === 0 && <p className="text-xs text-stone-500">No documents uploaded yet.</p>}</div><details className="my-3"><summary className="cursor-pointer text-xs text-stone-600">Have an existing proposal ID?</summary><form onSubmit={load} className="my-2 flex flex-wrap items-end gap-2"><label className="block text-sm">Existing proposal ID<input value={existingId} onChange={e => setExistingId(e.target.value)} className="block rounded border p-2" /></label><button disabled={busy || !existingId.trim()} className="rounded border p-2">Load proposal</button></form></details>
    {canUpload && !record && <form onSubmit={upload} className="space-y-3"><label className="block">Document title<input required maxLength={200} value={title} onChange={e => setTitle(e.target.value)} className="ml-2 rounded border p-2" /></label><label className="block">PDF file<input disabled={busy} type="file" accept=".pdf,application/pdf" onChange={e => { setFile(e.target.files?.[0] ?? null); setError(''); }} className="block max-w-full p-2" /></label><button disabled={busy || !file || !title.trim()} className="rounded-lg bg-[#7a1b32] px-4 py-2 text-white disabled:opacity-50">{busy ? 'Uploading…' : 'Upload proposal'}</button></form>}
    {record && <div><p role="status">Saved {record.title} · Revision {record.revision} · {record.status}</p><p className="break-all text-xs">Proposal ID: {record.id}</p><button disabled={busy} onClick={download} className="my-3 underline">Get fresh download link</button>{url && <a href={url} target="_blank" rel="noreferrer" className="ml-3 underline">Download PDF (expires in 15 minutes)</a>}
      {record && <p className="mt-3 rounded-lg bg-blue-50 p-3 text-xs text-blue-900" role="status">{nextReviewStep}</p>}
      {canReview && readyForThisReviewer && <div className="mt-4 rounded-xl border border-stone-200 bg-stone-50/70 p-4"><label className="block text-xs font-semibold text-stone-700">Document review note ({isFacultyAdvisor ? 'Club faculty advisor' : 'Campus administrator'})<textarea value={note} onChange={e => setNote(e.target.value)} className="mt-1 block w-full rounded border p-2 text-xs" /></label><p className="mt-2 text-xs text-amber-900">Document approval does not confirm the event or reserve a venue. Faculty approval moves the document to campus review; only campus approval completes the document review. Neither step confirms an event or reserves a venue.</p><div className="my-2 flex flex-wrap gap-3">{(['approve', 'reject', 'request_revision'] as const).map(action => <button key={action} disabled={busy} onClick={() => review(action)} className="rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-xs font-medium text-stone-800 shadow-2xs hover:bg-stone-50 active:scale-[0.98]">{action.replaceAll('_', ' ')}</button>)}</div></div>}
    </div>}{error && <p role="alert" className="text-rose-800">{error}</p>}
  </section>;
}
