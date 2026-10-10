import React from 'react';
import { MapPin, Users, AlertTriangle, Info, CheckCircle2, Building2 } from 'lucide-react';

export interface ResourceProps {
  id: string;
  name: string;
  type: string;
  capacity?: number;
  location?: string;
  source: string;
  responsibleOffice: string;
  availabilityStatus: 'unknown' | 'unverified' | 'available';
  description?: string;
}

export const ResourceCard: React.FC<{ resource: ResourceProps }> = ({ resource }) => {
  return (
    <div className="bg-white rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.08)] hover:shadow-[0_8px_30px_rgb(122,27,50,0.06)] transition-all duration-300 overflow-hidden flex flex-col h-full group border-none">
      <div className="p-6 flex-grow">
        <div className="flex justify-between items-start mb-4">
          <h3 className="text-xl font-bold text-gray-900 tracking-tight group-hover:text-[#7a1b32] transition-colors">{resource.name}</h3>
          <span className="inline-flex items-center rounded-full bg-[#FFF5F0] px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-[#7a1b32] shadow-sm border border-rose-50">
            {resource.type}
          </span>
        </div>
        
        <p className="text-sm text-gray-500 mb-6 line-clamp-3 leading-relaxed">{resource.description}</p>
        
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

        <div className="mt-4 pt-5 border-t border-stone-100 border-dashed">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center rounded-md bg-stone-50 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-gray-400">
              Source: {resource.source}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-auto border-t border-stone-100">
        {resource.availabilityStatus === 'unknown' && (
          <div className="bg-amber-50/50 px-6 py-4 flex items-center">
            <AlertTriangle className="h-4 w-4 text-amber-500 mr-2 flex-shrink-0" />
            <span className="text-xs font-bold uppercase tracking-wider text-amber-700">
              Unknown until official confirmation
            </span>
          </div>
        )}
        {resource.availabilityStatus === 'unverified' && (
          <div className="bg-rose-50/50 px-6 py-4 flex items-center">
            <Info className="h-4 w-4 text-rose-500 mr-2 flex-shrink-0" />
            <span className="text-xs font-bold uppercase tracking-wider text-rose-700">
              Not verified
            </span>
          </div>
        )}
        {resource.availabilityStatus === 'available' && (
          <div className="bg-emerald-50/50 px-6 py-4 flex items-center">
            <CheckCircle2 className="h-4 w-4 text-emerald-500 mr-2 flex-shrink-0" />
            <span className="text-xs font-bold uppercase tracking-wider text-emerald-700">
              Likely Available
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
