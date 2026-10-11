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
  return <section className="rounded-[10px] border border-stone-200/80 bg-white/95 p-6 shadow-sm backdrop-blur-xl"><h2 className="text-xl font-bold tracking-tight text-stone-900">Ask CampusCue</h2><p className="my-2 text-sm text-stone-600">Answers rely on approved evidence. Review citations and action drafts before making decisions.</p>
    {!token && <p className="text-sm font-medium text-stone-500">Sign in through the profile menu to ask a question.</p>}
    <div aria-live="polite" className="space-y-4">{turns.map((turn, i) => <article key={i} className={'rounded-[10px] p-4.5 transition-all ' + (turn.role === 'user' ? 'border border-rose-100 bg-rose-50/70' : 'border border-stone-200/80 bg-stone-50/60')}><p className="text-xs font-bold uppercase tracking-wider text-stone-500">{turn.role}</p><p className="mt-2 whitespace-pre-wrap text-sm text-stone-900 leading-relaxed">{turn.content}</p>
      {turn.response?.clarifying_question && <p className="mt-3 text-sm font-semibold text-[#7a1b32]">{turn.response.clarifying_question}</p>}
      {turn.response?.citations?.map(citation => { const url = sourceUrl(citation.source_url); return <blockquote key={citation.evidence_id} className="my-3 rounded-[8px] border-l-4 border-[#7a1b32] bg-white/80 p-3 text-sm shadow-xs"><p className="font-semibold text-stone-800">{citation.title} · pp. {citation.page_start}–{citation.page_end} · Version {citation.document_version}</p><p className="my-1.5 whitespace-pre-wrap text-stone-600 leading-normal">{citation.excerpt}</p>{url && <a href={url + (url.includes('#') ? '' : '#page=' + citation.page_start)} target="_blank" rel="noreferrer" className="text-xs font-semibold text-[#7a1b32] underline hover:text-[#631628]">Open source</a>}<p className="break-all text-[11px] text-stone-400 mt-1">Evidence: {citation.evidence_id}</p></blockquote>; })}
      {turn.response && !turn.response.citations?.length && <p className="mt-2 text-xs text-stone-400">No document citations returned for this reply.</p>}
      {turn.response?.proposed_actions?.map(action => <ActionReview key={action.action_id} action={action} />)}
      {Boolean(turn.response?.trace?.length) && <details className="mt-3 text-xs text-stone-500"><summary className="cursor-pointer font-medium hover:text-stone-700">Tool activity</summary>{turn.response?.trace?.map((trace, n) => <p key={n} className="mt-1">{trace.tool}: {trace.outcome} · {trace.latency_ms} ms</p>)}</details>}
      {turn.response && <p className="mt-2 text-[11px] text-stone-400">Request: {turn.response.request_id}</p>}
    </article>)}</div>
    <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
      <span className="font-medium text-stone-500">Demo prompts:</span>
      <button type="button" onClick={() => setInput('Plan a workshop for Synthetic Robotics Club in Synthetic Main Auditorium on 24 November 2026 from 3pm to 5pm.')} className="rounded-[10px] border border-rose-200/80 bg-rose-50/70 px-3 py-1.5 text-[#7a1b32] shadow-xs transition-all duration-150 hover:bg-rose-100 active:scale-[0.98]">
        📅 Plan Robotics Workshop
      </button>
      <button type="button" onClick={() => setInput('Plan an event in Synthetic Main Auditorium on 20 November 2026 from 10am to 11am.')} className="rounded-[10px] border border-amber-200/80 bg-amber-50/70 px-3 py-1.5 text-amber-900 shadow-xs transition-all duration-150 hover:bg-amber-100 active:scale-[0.98]">
        ⚠️ Test Conflicting Slot
      </button>
    </div>
    <form onSubmit={send} className="mt-3 space-y-3">
      <label className="block text-sm font-medium text-stone-700">Policy question
        <textarea
          disabled={busy || !token}
          required
          maxLength={4000}
          rows={3}
          placeholder="Ask anything about student affairs, venue permissions, budget policies, or event planning... (e.g., What are the rules for organizing a workshop after 8 PM?)"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
              e.preventDefault();
              send(e);
            }
          }}
          className="mt-2 w-full rounded-[10px] border border-stone-300/80 bg-white p-3 text-sm transition-all focus:border-[#7a1b32] focus:outline-none focus:ring-2 focus:ring-[#7a1b32]/15"
        />
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <button
          disabled={busy || !token || !input.trim()}
          className="rounded-[10px] bg-[#7a1b32] px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition-all duration-150 ease-out hover:bg-[#631628] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? 'Asking…' : 'Ask CampusCue'}
        </button>
        {!input.trim() && token && (
          <span className="text-xs text-stone-400 font-medium">
            Type a question above or click one of the demo prompts to enable.
          </span>
        )}
      </div>
      {error && <p role="alert" className="text-sm font-medium text-rose-800">{error}</p>}
    </form>
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
  return <section className="my-3 rounded-[10px] border border-stone-200/80 bg-white p-4.5 shadow-sm"><h3 className="font-bold text-stone-900">Action draft: {action.type}</h3><p className="mt-1 text-sm text-stone-600">{action.summary}</p><p className="mt-1 text-xs font-semibold text-[#7a1b32]">{status}</p><details className="my-2"><summary className="cursor-pointer text-xs font-medium text-stone-500 hover:text-stone-700">Review proposed fields</summary><pre className="overflow-auto whitespace-pre-wrap rounded-[8px] bg-stone-50 p-2 text-xs text-stone-700 mt-1">{JSON.stringify(action.payload, null, 2)}</pre></details>
    {Boolean(action.conflicts?.length) && <ConflictSidebar result={{ event_id: action.target_event_id, evaluated_as: 'DRAFT', conflicts: action.conflicts!, has_blocking: action.conflicts!.some(c => c.severity === 'blocking'), checked_at: action.created_at }} />}
    {status === 'PROPOSED' && <div className="my-3 flex gap-3"><button disabled={busy || action.type !== 'CREATE_EVENT_DRAFT'} onClick={() => decide(true)} className="rounded-[10px] bg-[#7a1b32] px-4 py-2 text-xs font-semibold text-white shadow-xs transition-all duration-150 hover:bg-[#631628] active:scale-[0.98] disabled:opacity-50">Confirm draft creation</button><button disabled={busy} onClick={() => decide(false)} className="rounded-[10px] border border-stone-300 bg-white px-4 py-2 text-xs font-semibold text-stone-700 transition-all duration-150 hover:bg-stone-50 active:scale-[0.98]">Reject action</button></div>}
    {action.type !== 'CREATE_EVENT_DRAFT' && <p className="text-xs text-stone-500">Core does not support execution of this action type yet.</p>}
    {created && <Link className="mt-2 inline-block text-xs font-semibold text-[#7a1b32] underline" href={'/changes?eventId=' + created}>Open created event draft</Link>}
    {error && <p role="alert" className="text-sm font-medium text-rose-800">{error}</p>}
  </section>;
}
