'use client';
import { useState } from 'react';
import type { FormEvent } from 'react';
import { useAuth } from '@/context/AuthContext';
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
  const role = session?.user.memberships?.find(m => m.club_id === clubId)?.role;
  const canUpload = session?.user.campus_admin || role === 'ORGANIZER' || role === 'CLUB_ADMIN';
  async function upload(event: FormEvent) {
    event.preventDefault(); if (!token || !file || busy) return;
    const invalid = validateProposal(file); if (invalid) { setError(invalid); return; }
    setBusy(true); setError(''); setUrl('');
    try { setRecord(await proposalsApi.upload(token, clubId, eventId, file, title.trim())); setFile(null); }
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
    try { setRecord(await proposalsApi.review(token, record.id, { action, review_note: note.trim() || null })); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); }
  }
  return <section className="mt-6 rounded-2xl border bg-white p-5"><h2 className="text-xl font-bold">Proposal document</h2><p className="my-2 text-sm">PDF only, up to 15 MiB. Uploading a proposal does not confirm the event.</p>
    {canUpload && !record && <form onSubmit={upload} className="space-y-3"><label className="block">Document title<input required maxLength={200} value={title} onChange={e => setTitle(e.target.value)} className="ml-2 rounded border p-2" /></label><label className="block">PDF file<input disabled={busy} type="file" accept=".pdf,application/pdf" onChange={e => { setFile(e.target.files?.[0] ?? null); setError(''); }} className="block max-w-full p-2" /></label><button disabled={busy || !file || !title.trim()} className="rounded-lg bg-[#7a1b32] px-4 py-2 text-white disabled:opacity-50">{busy ? 'Uploading…' : 'Upload proposal'}</button></form>}
    {record && <div><p role="status">Saved {record.title} · Revision {record.revision} · {record.status}</p><p className="break-all text-xs">Proposal ID: {record.id}</p><button disabled={busy} onClick={download} className="my-3 underline">Get fresh download link</button>{url && <a href={url} target="_blank" rel="noreferrer" className="ml-3 underline">Download PDF (expires in 15 minutes)</a>}
      {session?.user.campus_admin && <div><label>Review note<textarea value={note} onChange={e => setNote(e.target.value)} className="block w-full rounded border p-2" /></label><div className="my-2 flex flex-wrap gap-3">{(['approve', 'reject', 'request_revision'] as const).map(action => <button key={action} disabled={busy} onClick={() => review(action)} className="rounded border p-2">{action.replaceAll('_', ' ')}</button>)}</div></div>}
    </div>}{error && <p role="alert" className="text-rose-800">{error}</p>}
  </section>;
}
