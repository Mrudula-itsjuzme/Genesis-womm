import ChangeImpactList from '@/components/ChangeImpactList';
export default async function ChangesPage({ searchParams }: { searchParams: Promise<{ eventId?: string }> }) {
  const { eventId } = await searchParams;
  return <section className="mx-auto max-w-6xl p-4 md:p-8"><h1 className="text-3xl font-bold text-[#7a1b32]">Event details and change preview</h1><p className="my-4">Inspect live records, review scheduling advice, and progress the authorized event lifecycle.</p><ChangeImpactList initialEventId={eventId} /></section>;
}
