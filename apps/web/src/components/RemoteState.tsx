'use client';
export default function RemoteState({
  signedIn,
  loading,
  error,
  retry,
  empty,
}: {
  signedIn: boolean;
  loading: boolean;
  error?: string;
  retry: () => void;
  empty?: boolean;
}) {
  if (!signedIn)
    return (
      <div className="rounded-[10px] border border-stone-200/80 bg-stone-50/60 p-6 text-center">
        <p className="text-sm font-medium text-stone-600">Sign in using the profile menu to load campus data.</p>
      </div>
    );
  if (loading)
    return (
      <div role="status" className="rounded-[10px] border border-stone-200/80 bg-white p-8 text-center">
        <div className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-stone-300 border-t-[#7a1b32]" />
        <p className="mt-2 text-xs font-medium text-stone-500">Loading campus events…</p>
      </div>
    );
  if (error)
    return (
      <div role="alert" className="rounded-[10px] border border-rose-200 bg-rose-50/70 p-5">
        <p className="text-sm font-semibold text-rose-900">{error}</p>
        <button
          onClick={retry}
          className="mt-3 rounded-[8px] bg-[#7a1b32] px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs transition hover:bg-[#631628] active:scale-[0.98]"
        >
          Try again
        </button>
      </div>
    );
  if (empty)
    return (
      <div className="rounded-[10px] border border-dashed border-stone-200 bg-stone-50/50 p-8 text-center">
        <p className="text-sm font-medium text-stone-500">No events found for this view.</p>
      </div>
    );
  return null;
}
