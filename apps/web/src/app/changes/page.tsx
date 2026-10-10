import React from 'react';
import ChangeImpactList from '@/components/ChangeImpactList';
import CommitmentBoard from '@/components/CommitmentBoard';
import ReportsSection from '@/components/ReportsSection';
import { ChevronDown } from 'lucide-react';

export default function ChangesPage() {
  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Change Impact</h1>
          <p className="text-sm text-gray-500 mt-1">Review the downstream effects of recent updates.</p>
        </div>
        
        <div className="relative">
          <button className="flex items-center gap-2 bg-white border border-gray-300 rounded-md py-2 px-4 text-sm font-medium text-gray-700 hover:bg-gray-50 shadow-sm">
            INIT AI Hackathon
            <ChevronDown className="w-4 h-4 text-gray-500" />
          </button>
        </div>
      </div>

      <ChangeImpactList />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <CommitmentBoard />
        </div>
        <div className="lg:col-span-1">
          <ReportsSection />
        </div>
      </div>
    </div>
  );
}
