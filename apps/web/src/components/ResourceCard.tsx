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
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200 overflow-hidden flex flex-col h-full">
      <div className="p-5 flex-grow">
        <div className="flex justify-between items-start mb-2">
          <h3 className="text-lg font-semibold text-gray-900">{resource.name}</h3>
          <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10">
            {resource.type}
          </span>
        </div>
        
        <p className="text-sm text-gray-500 mb-4 line-clamp-2">{resource.description}</p>
        
        <div className="space-y-2 mb-4">
          {resource.capacity && (
            <div className="flex items-center text-sm text-gray-600">
              <Users className="w-4 h-4 mr-2 text-gray-400" />
              <span>Capacity: {resource.capacity}</span>
            </div>
          )}
          {resource.location && (
            <div className="flex items-center text-sm text-gray-600">
              <MapPin className="w-4 h-4 mr-2 text-gray-400" />
              <span>{resource.location}</span>
            </div>
          )}
          <div className="flex items-center text-sm text-gray-600">
            <Building2 className="w-4 h-4 mr-2 text-gray-400" />
            <span>Office: {resource.responsibleOffice}</span>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t border-gray-100">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center rounded bg-gray-50 px-2 py-1 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-500/10">
              Source: {resource.source}
            </span>
          </div>
        </div>
      </div>

      <div className="mt-auto border-t border-gray-100">
        {resource.availabilityStatus === 'unknown' && (
          <div className="bg-amber-50 px-4 py-3 flex items-start">
            <AlertTriangle className="h-5 w-5 text-amber-600 mr-2 flex-shrink-0" />
            <span className="text-sm text-amber-800">
              Availability: Unknown until official confirmation
            </span>
          </div>
        )}
        {resource.availabilityStatus === 'unverified' && (
          <div className="bg-orange-50 px-4 py-3 flex items-start">
            <Info className="h-5 w-5 text-orange-600 mr-2 flex-shrink-0" />
            <span className="text-sm text-orange-800">
              Not verified
            </span>
          </div>
        )}
        {resource.availabilityStatus === 'available' && (
          <div className="bg-green-50 px-4 py-3 flex items-start">
            <CheckCircle2 className="h-5 w-5 text-green-600 mr-2 flex-shrink-0" />
            <span className="text-sm text-green-800">
              Likely Available
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
