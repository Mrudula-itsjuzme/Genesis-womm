import React from 'react';
import { MapPin, Users, AlertTriangle, Info, CheckCircle2, Building2, ExternalLink } from 'lucide-react';

export interface ResourceProps {
  id: string;
  name: string;
  type: string;
  capacity?: number;
  location?: string;
  source: string;
  sourceUrl?: string;
  responsibleOffice: string;
  availabilityStatus: 'unknown' | 'unverified' | 'available';
  description?: string;
}

export const ResourceCard: React.FC<{ resource: ResourceProps }> = ({ resource }) => {
  return (
    <article className="flex h-full min-w-0 flex-col overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm transition-shadow hover:shadow-md">
      <div className="flex-grow p-5 sm:p-6">
        <div className="mb-4 flex min-w-0 flex-wrap items-start justify-between gap-3">
          <h3 className="min-w-0 break-words text-lg font-bold text-gray-900 transition-colors group-hover:text-[#7a1b32]">{resource.name}</h3>
          <span className="inline-flex max-w-full shrink-0 items-center rounded-full border border-rose-50 bg-[#FFF5F0] px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-[#7a1b32]">
            {resource.type}
          </span>
        </div>

        <p className="mb-5 line-clamp-3 break-words text-sm leading-relaxed text-gray-600">{resource.description}</p>

        <div className="space-y-3 mb-6">
          {resource.capacity && (
            <div className="flex items-center text-xs font-semibold text-gray-600 tracking-wide uppercase">
              <div className="w-6 h-6 rounded-md bg-stone-50 flex items-center justify-center mr-3">
                <Users className="w-3.5 h-3.5 text-gray-400" />
              </div>
              <span>Capacity: {resource.capacity}</span>
            </div>
          )}
          {resource.location && (
            <div className="flex items-center text-xs font-semibold text-gray-600 tracking-wide uppercase">
              <div className="w-6 h-6 rounded-md bg-stone-50 flex items-center justify-center mr-3">
                <MapPin className="w-3.5 h-3.5 text-gray-400" />
              </div>
              <span>{resource.location}</span>
            </div>
          )}
          <div className="flex items-center text-xs font-semibold text-gray-600 tracking-wide uppercase">
            <div className="w-6 h-6 rounded-md bg-stone-50 flex items-center justify-center mr-3">
              <Building2 className="w-3.5 h-3.5 text-gray-400" />
            </div>
            <span>Office: {resource.responsibleOffice}</span>
          </div>
        </div>

        <div className="mt-4 border-t border-dashed border-stone-100 pt-4">
          {resource.sourceUrl ? (
            <a
              href={resource.sourceUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex max-w-full items-center gap-1.5 break-all text-xs font-semibold text-[#7a1b32] underline decoration-rose-200 underline-offset-2 hover:text-[#541224]"
            >
              <span className="break-words">Source: {resource.source}</span>
              <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              <span className="sr-only"> (opens in a new tab)</span>
            </a>
          ) : (
            <span className="text-xs font-semibold text-gray-500">Source: {resource.source}</span>
          )}
        </div>
      </div>

      <div className="mt-auto border-t border-stone-100">
        {resource.availabilityStatus === 'unknown' && (
          <div className="flex items-start gap-2 bg-amber-50/70 px-5 py-4">
            <AlertTriangle className="h-4 w-4 text-amber-500 mr-2 flex-shrink-0" />
            <span className="text-xs font-bold leading-5 text-amber-800">
              Unknown until official confirmation
            </span>
          </div>
        )}
        {resource.availabilityStatus === 'unverified' && (
          <div className="flex items-start gap-2 bg-rose-50/70 px-5 py-4">
            <Info className="h-4 w-4 text-rose-500 mr-2 flex-shrink-0" />
            <span className="text-xs font-bold leading-5 text-rose-800">
              Listing unverified; confirm with responsible office
            </span>
          </div>
        )}
        {resource.availabilityStatus === 'available' && (
          <div className="flex items-start gap-2 bg-emerald-50/70 px-5 py-4">
            <CheckCircle2 className="h-4 w-4 text-emerald-500 mr-2 flex-shrink-0" />
            <span className="text-xs font-bold leading-5 text-emerald-800">
              Likely Available
            </span>
          </div>
        )}
      </div>
    </article>
  );
};
