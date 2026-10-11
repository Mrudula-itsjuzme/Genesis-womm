'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { useRemote } from '@/hooks/useRemote';
import { resourcesApi } from '@/lib/api/endpoints';
import { ResourceCard } from '@/components/ResourceCard';
import RemoteState from '@/components/RemoteState';
export default function VenuesPage() {
  const { token } = useAuth(); const [query, setQuery] = useState(''); const [offset, setOffset] = useState(0);
  const remote = useRemote(token && token + query + offset, signal => resourcesApi.list(token!, { kind: 'VENUE', q: query || undefined, limit: 30, offset }, signal));
  return <section className="mx-auto max-w-7xl p-4 md:p-8"><Link className="underline" href="/resources">Resource library</Link><h1 className="my-4 text-3xl font-bold text-[#7a1b32]">Explore venues</h1><p>Recorded resources and provenance from Core. An empty result does not imply availability.</p>
    <label className="my-5 block">Find a venue<input className="ml-3 max-w-full rounded-lg border bg-white p-3" value={query} onChange={e => { setQuery(e.target.value); setOffset(0); }} /></label>
    <RemoteState signedIn={Boolean(token)} {...remote} empty={remote.data?.items.length === 0} />
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{remote.data?.items.map(resource => <ResourceCard key={resource.id} resource={resource} />)}</div>
    {remote.data && <div className="my-5 flex gap-4"><button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 30))}>Previous</button><span>{remote.data.total} venues</span><button disabled={offset + 30 >= remote.data.total} onClick={() => setOffset(offset + 30)}>Next</button></div>}
  </section>;
}
