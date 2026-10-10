import type { ResourceOut } from '@/types/core-api';
import { campusFormat } from '@/lib/campus-time';
import { sourceUrl } from '@/lib/source-url';
export function ResourceCard({ resource }: { resource: ResourceOut }) {
  const url = sourceUrl(resource.source_url);
  return <article className="space-y-3 rounded-2xl border bg-white p-5"><div><h2 className="text-xl font-bold">{resource.name}</h2><p className="text-xs">{resource.kind}{resource.synthetic ? ' · Synthetic demo' : ''}</p></div>
    <p>{resource.description ?? 'No description recorded.'}</p><p>{resource.location ?? 'Location not recorded.'}</p><p>Capacity: {resource.capacity ?? 'Unknown'}</p>
    <p className="rounded-lg bg-amber-50 p-3 text-sm">Availability: {resource.availability_state}. Confirm allocation with the responsible office for your event.</p>
    <p className="text-xs">Source: {resource.source_id} · Freshness: {resource.freshness_state}</p>
    <p className="text-xs">Last checked: {resource.last_checked_at ? campusFormat(resource.last_checked_at) : 'Unknown'}<br />Collected: {resource.collected_at ? campusFormat(resource.collected_at) : 'Unknown'}</p>
    {url && <a href={url} target="_blank" rel="noreferrer" className="text-sm underline">Open recorded source</a>}
  </article>;
}
