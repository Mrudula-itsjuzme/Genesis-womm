import type { ConflictCheckOut } from '@/types/core-api';
import { campusFormat } from '@/lib/campus-time';
export default function ConflictSidebar({ result, loading = false, error }: { result?: ConflictCheckOut; loading?: boolean; error?: string }) {
  return <aside className="rounded-2xl border border-stone-200 bg-white p-5" aria-label="Scheduling advice">
    <h2 className="text-xl font-bold">Scheduling advice</h2>
    <p className="my-2 text-xs">Advisory checks are repeated by Core when confirming. The configurable 120-minute campus gap is a planning assumption.</p>
    {loading ? <p role="status">Checking schedule…</p> : error ? <p role="alert">{error}</p> : !result ? <p>Enter a valid schedule to check potential conflicts.</p> : <>
      <p className="text-sm">Evaluated as {result.evaluated_as} at {campusFormat(result.checked_at)}.</p>
      {!result.conflicts.length && <p className="mt-3">No recorded conflicts found. Venue availability still requires authorized confirmation.</p>}
      <div className="mt-3 space-y-3">{result.conflicts.map((conflict, index) => <article key={index} className={'rounded-xl border p-3 ' + (conflict.severity === 'blocking' ? 'border-rose-300 bg-rose-50' : conflict.severity === 'warning' ? 'border-amber-300 bg-amber-50' : 'border-stone-200')}>
        <h3 className="font-bold">{conflict.type.replaceAll('_', ' ')}</h3><p className="text-xs uppercase">{conflict.severity}{conflict.override_required ? ' · Scoped override required' : ''}</p>
        <p className="mt-2 text-sm">{conflict.message}</p>
        {conflict.with_event && <p className="mt-2 text-sm">{conflict.with_event.title} · {conflict.with_event.club_name} · {conflict.with_event.resource_name ?? 'Venue unspecified'}</p>}
        <p className="mt-1 text-xs">{campusFormat(conflict.start_at)} – {campusFormat(conflict.end_at)}</p>
      </article>)}</div>
    </>}
  </aside>;
}
