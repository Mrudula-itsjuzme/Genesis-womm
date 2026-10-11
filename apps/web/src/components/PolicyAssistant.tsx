'use client';
import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { agentApi } from '@/lib/api/endpoints';
import { errorMessage } from '@/lib/api/client';
import { sourceUrl } from '@/lib/source-url';
import type { ChatMessage, ChatResponse, AgentAction } from '@/types/core-api';
import ConflictSidebar from './ConflictSidebar';

type Turn = ChatMessage & { response?: ChatResponse };
export function PolicyAssistant() {
  const { token } = useAuth();
  return <Conversation key={token} />;
}
function Conversation() {
  const { token } = useAuth();
  const [turns, setTurns] = useState<Turn[]>([]); const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const alive = useRef(true); const abort = useRef<AbortController | null>(null);
  useEffect(() => { alive.current = true; return () => { alive.current = false; abort.current?.abort(); }; }, []);
  async function send(event: FormEvent) {
    event.preventDefault(); if (!token || busy || !input.trim()) return;
    const question = input.trim();
    const history: ChatMessage[] = [...turns.map(({ role, content }) => ({ role, content: content.slice(0, 4000) })), { role: 'user' as const, content: question }].slice(-19);
    setBusy(true); setError(''); abort.current = new AbortController();
    try {
      const response = await agentApi.chat(token, history, null, abort.current.signal);
      if (!alive.current) return;
      setTurns(previous => [...previous, { role: 'user', content: question }, { role: 'assistant', content: response.message, response }]); setInput('');
    } catch (err) { if (alive.current) setError(errorMessage(err)); }
    finally { if (alive.current) setBusy(false); }
  }
  return <section className="rounded-2xl border bg-white p-5"><h2 className="text-xl font-bold">Ask CampusCue</h2><p className="my-3 text-sm">Answers rely on approved evidence. Review citations and action drafts before making decisions.</p>
    {!token && <p>Sign in through the profile menu to ask a question.</p>}
    <div aria-live="polite" className="space-y-4">{turns.map((turn, i) => <article key={i} className={'rounded-xl p-4 ' + (turn.role === 'user' ? 'bg-rose-50' : 'border bg-stone-50')}><p className="text-xs font-bold uppercase">{turn.role}</p><p className="mt-2 whitespace-pre-wrap">{turn.content}</p>
      {turn.response?.clarifying_question && <p className="mt-3 font-semibold">{turn.response.clarifying_question}</p>}
      {turn.response?.citations?.map(citation => { const url = sourceUrl(citation.source_url); return <blockquote key={citation.evidence_id} className="my-3 border-l-4 border-rose-200 pl-3 text-sm"><p>{citation.title} · pp. {citation.page_start}–{citation.page_end} · Version {citation.document_version}</p><p className="my-2 whitespace-pre-wrap">{citation.excerpt}</p>{url && <a href={url + (url.includes('#') ? '' : '#page=' + citation.page_start)} target="_blank" rel="noreferrer" className="underline">Open source</a>}<p className="break-all text-xs">Evidence: {citation.evidence_id}</p></blockquote>; })}
      {turn.response && !turn.response.citations?.length && <p className="mt-2 text-xs">No document citations returned for this reply.</p>}
      {turn.response?.proposed_actions?.map(action => <ActionReview key={action.action_id} action={action} />)}
      {Boolean(turn.response?.trace?.length) && <details className="mt-3 text-xs"><summary>Tool activity</summary>{turn.response?.trace?.map((trace, n) => <p key={n}>{trace.tool}: {trace.outcome} · {trace.latency_ms} ms</p>)}</details>}
      {turn.response && <p className="mt-2 text-xs">Request: {turn.response.request_id}</p>}
    <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
      <span className="font-medium text-stone-500">Demo prompts:</span>
      <button type="button" onClick={() => setInput('Plan a workshop for Synthetic Robotics Club in Synthetic Main Auditorium on 24 November 2026 from 3pm to 5pm.')} className="rounded-full border border-rose-200 bg-rose-50/60 px-3 py-1 text-[#7a1b32] transition hover:bg-rose-100">
        📅 Plan Robotics Workshop
      </button>
      <button type="button" onClick={() => setInput('Plan an event in Synthetic Main Auditorium on 20 November 2026 from 10am to 11am.')} className="rounded-full border border-amber-200 bg-amber-50/60 px-3 py-1 text-amber-900 transition hover:bg-amber-100">
        ⚠️ Test Conflicting Slot
      </button>
    </div>
    <form onSubmit={send} className="mt-3 space-y-3"><label className="block">Policy question<textarea disabled={busy || !token} required maxLength={4000} value={input} onChange={e => setInput(e.target.value)} className="mt-2 w-full rounded-xl border p-3" /></label><button disabled={busy || !token || !input.trim()} className="rounded-xl bg-[#7a1b32] px-5 py-3 text-white disabled:opacity-50">{busy ? 'Asking…' : 'Ask CampusCue'}</button>{error && <p role="alert" className="text-rose-800">{error}</p>}</form>
  </section>;
}
function ActionReview({ action }: { action: AgentAction }) {
  const { token } = useAuth(); const [status, setStatus] = useState(action.status);
  const [busy, setBusy] = useState(false); const [error, setError] = useState(''); const [created, setCreated] = useState('');
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  async function decide(confirm: boolean) {
    if (!token || busy) return; setBusy(true); setError('');
    try {
      if (confirm) { const result = await agentApi.confirmAction(token, action.action_id); if (alive.current) { setStatus(result.action.status); setCreated(result.created_entity_id ?? ''); } }
      else { const result = await agentApi.rejectAction(token, action.action_id); if (alive.current) setStatus(result.status); }
    } catch (err) { if (alive.current) setError(errorMessage(err)); }
    finally { if (alive.current) setBusy(false); }
  }
  return <section className="my-3 rounded-xl border bg-white p-4"><h3 className="font-bold">Action draft: {action.type}</h3><p>{action.summary}</p><p className="text-xs">{status}</p><details className="my-2"><summary>Review proposed fields</summary><pre className="overflow-auto whitespace-pre-wrap text-xs">{JSON.stringify(action.payload, null, 2)}</pre></details>
    {Boolean(action.conflicts?.length) && <ConflictSidebar result={{ event_id: action.target_event_id, evaluated_as: 'DRAFT', conflicts: action.conflicts!, has_blocking: action.conflicts!.some(c => c.severity === 'blocking'), checked_at: action.created_at }} />}
    {status === 'PROPOSED' && <div className="my-3 flex gap-3"><button disabled={busy || action.type !== 'CREATE_EVENT_DRAFT'} onClick={() => decide(true)} className="rounded border p-2">Confirm draft creation</button><button disabled={busy} onClick={() => decide(false)} className="rounded border p-2">Reject action</button></div>}
    {action.type !== 'CREATE_EVENT_DRAFT' && <p className="text-xs">Core does not support execution of this action type yet.</p>}
    {created && <Link className="underline" href={'/changes?eventId=' + created}>Open created event draft</Link>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
