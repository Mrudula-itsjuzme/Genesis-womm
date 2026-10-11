import type { ConflictCheckOut } from '@/types/core-api';
import { campusFormat } from '@/lib/campus-time';
export default function ConflictSidebar({ result, loading = false, error }: { result?: ConflictCheckOut; loading?: boolean; error?: string }) {
  return <aside className="rounded-2xl border border-stone-200 bg-white p-5" aria-label="Scheduling advice">
    <h2 className="text-xl font-bold">Scheduling advice</h2>
    <p className="my-2 text-xs">Advisory checks are repeated by Core when confirming. The campus gap is a configurable planning assumption; Core supplies the applicable conflict details.</p>
    {loading ? <p role="status">Checking schedule…</p> : error ? <p role="alert">{error}</p> : !result ? <p>Enter a valid schedule to check potential conflicts.</p> : <>
      <p className="text-sm">Evaluated as {result.evaluated_as} at {campusFormat(result.checked_at)}.</p>
      {!result.conflicts.length && <p className="mt-3">No recorded conflicts found. Venue availability still requires authorized confirmation.</p>}
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-sm">{conflict.type.replaceAll('_', ' ')}</h3>
          {conflict.constraint && <span className="rounded bg-amber-200/60 px-1.5 py-0.5 text-[10px] font-semibold text-amber-900 tracking-wider">{conflict.constraint}</span>}
        </div>
        <p className="text-xs uppercase font-medium mt-1">{conflict.severity}{conflict.override_required ? ' · Scoped override required' : ''}</p>
        <p className="mt-2 text-sm">{conflict.message}</p>
        {conflict.with_event && <p className="mt-2 text-sm">{conflict.with_event.title} · {conflict.with_event.club_name} · {conflict.with_event.resource_name ?? 'Venue unspecified'}</p>}
        <p className="mt-1 text-xs">{campusFormat(conflict.start_at)} – {campusFormat(conflict.end_at)}</p>
      </article>)}</div>
    </>}
  </aside>;
}
