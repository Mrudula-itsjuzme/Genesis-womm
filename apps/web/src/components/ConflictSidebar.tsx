import React from 'react';
import { AlertTriangle, User, CalendarX } from 'lucide-react';

const ConflictSidebar = () => {
  return (
    <div className="w-[380px] bg-white/50 backdrop-blur-xl border-l border-white/50 shadow-[0_0_40px_rgb(0,0,0,0.05)] p-6 flex flex-col h-full overflow-y-auto">
      <div className="mb-8">
        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2 tracking-tight">
          <div className="w-8 h-8 rounded-full bg-rose-100 flex items-center justify-center shadow-sm">
            <AlertTriangle className="w-4 h-4 text-rose-600" />
          </div>
          Potential Clash
        </h2>
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-500 mt-3 pl-10">
          Multiple interests for same venue
        </p>
      </div>

      <div className="bg-white rounded-2xl p-5 mb-8 shadow-sm border border-rose-100 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-24 h-24 bg-rose-50 rounded-full -mr-10 -mt-10 z-0"></div>
        <div className="relative z-10 flex items-start gap-4">
          <div className="flex-1">
            <h3 className="text-sm font-bold text-rose-900 uppercase tracking-wider mb-2">Venue Overlap Detected</h3>
            <p className="text-xs font-medium text-rose-800/80 leading-relaxed">
              Both events are requesting <strong className="text-rose-900">Acharya Hall</strong> at overlapping times on <strong className="text-rose-900">Day 5</strong>.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-4 flex-1">
        <div className="border border-stone-100 rounded-2xl p-5 bg-white shadow-[0_4px_20px_rgb(0,0,0,0.02)]">
          <div className="flex justify-between items-start mb-3">
            <span className="text-[10px] font-bold text-[#7a1b32] bg-rose-50 border border-rose-100 px-2.5 py-1 rounded-full uppercase tracking-wider shadow-sm">Event 1</span>
          </div>
          <h4 className="font-bold text-gray-900 text-base mb-1 tracking-tight">INIT AI Hackathon</h4>
          <p className="text-xs font-semibold text-gray-500 flex items-center gap-1.5 uppercase tracking-wider mb-1">
             10:00 AM - 4:00 PM
          </p>
          <p className="text-xs font-semibold text-gray-500 flex items-center gap-1.5 uppercase tracking-wider">
            <User className="w-3.5 h-3.5 text-gray-400" /> AI Club
          </p>
          <div className="mt-4 flex gap-2">
            <button className="flex-1 bg-white border border-stone-200 text-gray-700 text-xs font-bold py-2 rounded-xl hover:bg-stone-50 hover:border-stone-300 transition-all shadow-sm">
              Contact Organizer
            </button>
          </div>
        </div>

        <div className="flex items-center justify-center -my-1 relative z-10">
          <span className="text-rose-400 text-[10px] font-bold uppercase tracking-widest bg-[#FDF8F5] px-3 py-1 border border-rose-100 rounded-full shadow-sm">VS</span>
        </div>

        <div className="border border-stone-100 rounded-2xl p-5 bg-white shadow-[0_4px_20px_rgb(0,0,0,0.02)]">
          <div className="flex justify-between items-start mb-3">
            <span className="text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-100 px-2.5 py-1 rounded-full uppercase tracking-wider shadow-sm">Event 2</span>
          </div>
          <h4 className="font-bold text-gray-900 text-base mb-1 tracking-tight">IDEA Workshop</h4>
          <p className="text-xs font-semibold text-gray-500 flex items-center gap-1.5 uppercase tracking-wider mb-1">
            2:00 PM - 5:00 PM
          </p>
          <p className="text-xs font-semibold text-gray-500 flex items-center gap-1.5 uppercase tracking-wider">
            <User className="w-3.5 h-3.5 text-gray-400" /> Innovation Cell
          </p>
          <div className="mt-4 flex gap-2 flex-col">
            <button className="w-full bg-[#7a1b32] text-white text-xs font-bold py-2.5 rounded-xl hover:bg-[#5a1222] transition-colors shadow-md">
              Try Alternate Slot
            </button>
            <button className="w-full bg-white border border-stone-200 text-gray-700 text-xs font-bold py-2 rounded-xl hover:bg-stone-50 hover:border-stone-300 transition-all shadow-sm mt-1">
              Contact Organizer
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConflictSidebar;
