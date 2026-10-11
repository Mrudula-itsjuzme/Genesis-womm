import { Suspense } from 'react';
import ChangeImpactList from '@/components/ChangeImpactList';
type Params = { searchParams: Promise<{ eventId?: string }> };
async function SelectedEvent({ searchParams }: Params) {
  const { eventId } = await searchParams;
  return <ChangeImpactList initialEventId={eventId} />;
}
export default function ChangesPage({ searchParams }: Params) {
  return <section className="mx-auto max-w-6xl p-4 md:p-8"><h1 className="text-3xl font-bold text-[#7a1b32]">Event details and change preview</h1><p className="my-4">Inspect live records, review scheduling advice, and progress the authorized event lifecycle.</p><Suspense fallback={<p role="status">Loading selected event…</p>}><SelectedEvent searchParams={searchParams} /></Suspense></section>;
}
