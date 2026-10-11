import type { ConflictCheckOut } from '@/types/core-api';
import { campusFormat } from '@/lib/campus-time';
export default function ConflictSidebar({ result, loading = false, error }: { result?: ConflictCheckOut; loading?: boolean; error?: string }) {
  return <aside className="rounded-[10px] border border-stone-200/80 bg-white/95 p-5 shadow-sm backdrop-blur-xl" aria-label="Scheduling advice">
    <h2 className="text-xl font-bold tracking-tight text-stone-900">Scheduling advice</h2>
    <p className="my-2 text-xs text-stone-600">Advisory checks are repeated by Core when confirming. The campus gap is a configurable planning assumption; Core supplies the applicable conflict details.</p>
    {loading ? <p role="status" className="text-sm text-stone-500">Checking schedule…</p> : error ? <p role="alert" className="text-sm font-medium text-rose-800">{error}</p> : !result ? <p className="text-sm text-stone-500">Enter a valid schedule to check potential conflicts.</p> : <>
      <p className="text-sm font-medium text-stone-700">Evaluated as {result.evaluated_as} at {campusFormat(result.checked_at)}.</p>
      {!result.conflicts.length && <p className="mt-3 rounded-[10px] border border-emerald-200 bg-emerald-50/70 p-3 text-sm font-medium text-emerald-900">No recorded conflicts found. Venue availability still requires authorized confirmation.</p>}
      <div className="mt-3 space-y-3">{result.conflicts.map(conflict => <article key={`${conflict.type}-${conflict.start_at}-${conflict.end_at}`} className="rounded-[10px] border border-stone-200/80 bg-stone-50/50 p-3.5 transition-all">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-sm text-stone-900">{conflict.type.replaceAll('_', ' ')}</h3>
          {conflict.constraint && <span className="rounded-[6px] bg-amber-200/60 px-1.5 py-0.5 text-[10px] font-semibold text-amber-900 tracking-wider">{conflict.constraint}</span>}
        </div>
        <p className="text-xs uppercase font-medium mt-1 text-stone-500">{conflict.severity}{conflict.override_required ? ' · Scoped override required' : ''}</p>
        <p className="mt-2 text-sm text-stone-700">{conflict.message}</p>
        {conflict.with_event && <p className="mt-2 text-xs font-medium text-stone-600">{conflict.with_event.title} · {conflict.with_event.club_name} · {conflict.with_event.resource_name ?? 'Venue unspecified'}</p>}
        <p className="mt-1 text-xs text-stone-500">{campusFormat(conflict.start_at)} – {campusFormat(conflict.end_at)}</p>
      </article>)}</div>
    </>}
  </aside>;
}
