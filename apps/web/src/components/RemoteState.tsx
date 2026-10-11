'use client';
export default function RemoteState({ signedIn, loading, error, retry, empty }: { signedIn: boolean; loading: boolean; error?: string; retry: () => void; empty?: boolean }) {
  if (!signedIn) return <p className="rounded-xl bg-white p-6">Sign in using the profile menu to load campus data.</p>;
  if (loading) return <p role="status" className="p-6">Loading campus data…</p>;
  if (error) return <div role="alert" className="rounded-xl border border-rose-200 bg-white p-6"><p>{error}</p><button onClick={retry} className="mt-3 underline">Try again</button></div>;
  if (empty) return <p className="rounded-xl bg-white p-6">No records match this view.</p>;
  return null;
}
