import React from 'react';
import ChangeImpactList from '@/components/ChangeImpactList';
import CommitmentBoard from '@/components/CommitmentBoard';
import ReportsSection from '@/components/ReportsSection';
import { ChevronDown, BarChart2 } from 'lucide-react';

export default function ChangesPage() {
  return (
    <div className="min-h-screen font-sans bg-[#FAF9F8]">
      {/* Header Area */}
      <div className="bg-white border-b border-stone-200 shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-50 flex items-center justify-center text-[#7a1b32] border border-rose-100/50">
                <BarChart2 className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">Change Impact</h1>
                <p className="text-xs font-semibold text-gray-500 mt-0.5">Review downstream effects and commitments</p>
              </div>
            </div>
            
            <div className="relative">
              <button className="flex items-center gap-2 bg-white border border-stone-200 rounded-xl py-2.5 px-4 text-sm font-bold text-gray-800 hover:bg-stone-50 hover:border-stone-300 shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-rose-500/20">
                INIT AI Hackathon
                <ChevronDown className="w-4 h-4 text-gray-400" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-10 pb-20">
        <ChangeImpactList />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <CommitmentBoard />
          </div>
          <div className="lg:col-span-1">
            <ReportsSection />
          </div>
        </div>
      </div>
    </div>
  );
}
