'use client';

import React, { useState } from 'react';
import { ResourceCard, ResourceProps } from '@/components/ResourceCard';
import { PolicyAssistant } from '@/components/PolicyAssistant';

const MOCK_RESOURCES: ResourceProps[] = [
  {
    id: '1',
    name: 'Acharya Hall',
    type: 'Halls',
    capacity: 250,
    location: 'Main Block, 2nd Floor',
    source: 'Campus Master List',
    responsibleOffice: 'Dean of Administration',
    availabilityStatus: 'unknown',
    description: 'Medium capacity auditorium suitable for departmental events and guest lectures. Features built-in projector and PA system.'
  },
  {
    id: '2',
    name: 'Sudhamani Hall',
    type: 'Halls',
    capacity: 1500,
    location: 'Academic Block 3',
    source: 'Facilities DB',
    responsibleOffice: 'Registrar Office',
    availabilityStatus: 'unverified',
    description: 'Main campus auditorium for large-scale intercollege events, major cultural fests, and graduations.'
  },
  {
    id: '3',
    name: 'ICTS Audiovisual Support',
    type: 'ICTS / IT Services',
    source: 'ICTS Portal',
    responsibleOffice: 'IT Services',
    availabilityStatus: 'available',
    description: 'Provides technical support, sound engineering, and extra projection equipment for events. Must be booked 7 days in advance.'
  },
  {
    id: '4',
    name: 'Open Air Theatre',
    type: 'Facilities',
    capacity: 800,
    location: 'Near Student Center',
    source: 'Campus Master List',
    responsibleOffice: 'Student Affairs',
    availabilityStatus: 'available',
    description: 'Outdoor seating venue suitable for evening cultural events and informal gatherings.'
  }
];

const TABS = ['All', 'Halls', 'ICTS / IT Services', 'Facilities', 'Event Support'];

export default function ResourcesPage() {
  const [activeTab, setActiveTab] = useState('All');

  const filteredResources = activeTab === 'All' 
    ? MOCK_RESOURCES 
    : MOCK_RESOURCES.filter(r => r.type === activeTab);

  return (
    <div className="flex h-[calc(100vh-64px)] w-full overflow-hidden bg-gray-50">
      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <div className="p-8 max-w-7xl mx-auto w-full">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-6">Resource Explorer</h1>
            
            {/* Tabs */}
            <div className="border-b border-gray-200">
              <nav className="-mb-px flex space-x-8" aria-label="Tabs">
                {TABS.map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`
                      whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium transition-colors
                      ${activeTab === tab
                        ? 'border-indigo-500 text-indigo-600'
                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                      }
                    `}
                  >
                    {tab}
                  </button>
                ))}
              </nav>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6 pb-12">
            {filteredResources.map(resource => (
              <ResourceCard key={resource.id} resource={resource} />
            ))}
            {filteredResources.length === 0 && (
              <div className="col-span-full py-12 text-center text-gray-500">
                No resources found for this category.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Policy Assistant Sidebar */}
      <div className="w-[400px] flex-shrink-0 shadow-lg z-10 hidden lg:block">
        <PolicyAssistant />
      </div>
    </div>
  );
}
