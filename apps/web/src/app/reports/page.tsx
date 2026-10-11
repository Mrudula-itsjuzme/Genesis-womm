'use client';
import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useRemote } from '@/hooks/useRemote';
import { eventsApi, resourcesApi } from '@/lib/api/endpoints';
import { buildReport } from '@/lib/report';
import type { EventOut } from '@/types/core-api';
import RemoteState from '@/components/RemoteState';
export default function ReportsPage() {
  const { token } = useAuth();
  return <ReportSelector key={token} />;
}
function ReportSelector() {
  const { token } = useAuth(); const [id, setId] = useState(''); const [offset, setOffset] = useState(0);
  const list = useRemote(token && token + offset, signal => eventsApi.list(token!, { limit: 50, offset }, signal));
  const selected = useRemote(token && id ? token + id : null, signal => eventsApi.get(token!, id, signal));
  return <section className="mx-auto max-w-5xl p-4 md:p-8"><h1 className="text-3xl font-bold text-[#7a1b32]">Editable report drafts</h1><p className="my-3">Recorded event facts with placeholders for outcomes. Drafts are saved only in this browser.</p><label>Event<select className="my-4 ml-3 max-w-full rounded border bg-white p-3" value={id} onChange={e => setId(e.target.value)}><option value="">Select an event</option>{id && !list.data?.items.some(e => e.id === id) && <option value={id}>Selected event</option>}{list.data?.items.map(e => <option key={e.id} value={e.id}>{e.title}</option>)}</select></label><RemoteState signedIn={Boolean(token)} {...list} empty={list.data?.items.length === 0} />
    {list.data && <div className="mb-4 flex gap-4"><button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 50))}>Previous events</button><button disabled={offset + 50 >= list.data.total} onClick={() => setOffset(offset + 50)}>More events</button></div>}
    {id && <RemoteState signedIn={Boolean(token)} {...selected} />}{selected.data && <ReportEditor key={token + selected.data.id} event={selected.data} />}
  </section>;
}
function ReportEditor({ event }: { event: EventOut }) {
  const { token, session } = useAuth(); const [draft, setDraft] = useState(buildReport(event)); const [message, setMessage] = useState('');
  const venue = useRemote(token && event.resource_id ? token + event.resource_id : null, () => resourcesApi.get(token!, event.resource_id!));
  const key = 'campuscue.report.v1:' + session?.user.id + ':' + event.id;
  function save() { try { localStorage.setItem(key, draft); setMessage('Draft saved in this browser.'); } catch { setMessage('Browser storage is unavailable. Export the draft to keep it.'); } }
  function restore() { try { const stored = localStorage.getItem(key); if (stored !== null) { setDraft(stored); setMessage('Saved local draft restored. Verify it against the current event revision.'); } else setMessage('No saved local draft for this event.'); } catch { setMessage('Browser storage is unavailable.'); } }
  function exportDraft() {
    const url = URL.createObjectURL(new Blob([draft], { type: 'text/plain;charset=utf-8' }));
    const link = document.createElement('a'); link.href = url; link.download = 'campuscue-report-' + event.id + '.txt'; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function copyToClipboard() {
    try { await navigator.clipboard.writeText(draft); setMessage('Report draft copied to clipboard.'); }
    catch { setMessage('Clipboard permission denied.'); }
  }
  return <section className="rounded-2xl border bg-white p-5"><p className="mb-3">Current record: {event.status} · Revision {event.revision}</p><label className="block">Report text<textarea value={draft} onChange={e => setDraft(e.target.value)} className="mt-2 min-h-[28rem] w-full rounded-xl border p-4 text-sm font-mono" /></label><div className="my-4 flex flex-wrap gap-3"><button onClick={save} className="rounded border p-3 hover:bg-stone-50">Save local draft</button><button onClick={restore} className="rounded border p-3 hover:bg-stone-50">Restore local draft</button><button onClick={copyToClipboard} className="rounded border bg-stone-100 p-3 font-medium hover:bg-stone-200">Copy to clipboard</button><button onClick={exportDraft} className="rounded border p-3 hover:bg-stone-50">Export text</button><button onClick={() => { setDraft(buildReport(event, venue.data?.name)); setMessage('Draft regenerated from the current record.'); }} className="rounded border p-3 hover:bg-stone-50">Regenerate from record</button></div><p role="status" className="text-sm font-medium text-emerald-800">{message}</p></section>;
}
