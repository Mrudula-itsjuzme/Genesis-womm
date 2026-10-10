import React from 'react';
import { AlertCircle, ArrowRight, CheckCircle2 } from 'lucide-react';

export default function ChangeImpactList() {
  return (
    <div className="flex flex-col md:flex-row gap-6 mb-10">
      {/* Recent Change Card */}
      <div className="bg-[#FAF9F8] rounded-2xl shadow-sm border border-stone-200/50 p-6 flex-1">
        <h3 className="text-lg font-bold mb-4 text-gray-900">Recent Change</h3>
        <div className="flex items-center gap-4 bg-white border border-stone-100 shadow-sm p-4 rounded-xl">
          <div className="flex-1">
            <span className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1">Previous</span>
            <span className="font-medium text-gray-400 line-through">Acharya Hall</span>
          </div>
          <ArrowRight className="text-rose-900/40 w-5 h-5" />
          <div className="flex-1">
            <span className="block text-xs font-semibold uppercase tracking-wider text-rose-900/60 mb-1">Updated</span>
            <span className="font-bold text-[#7a1b32]">Seminar Hall II</span>
          </div>
        </div>
      </div>

      {/* Change Impact Checklist */}
      <div className="bg-[#FAF9F8] rounded-2xl shadow-sm border border-stone-200/50 p-6 flex-[2]">
        <h3 className="text-lg font-bold mb-4 text-gray-900 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-amber-500" />
          Change Impact
        </h3>
        <ul className="space-y-3">
          <li className="flex items-start gap-3 bg-white p-3 rounded-xl border border-stone-100 shadow-sm transition-shadow hover:shadow-md">
            <input type="checkbox" className="mt-1 h-4 w-4 rounded border-gray-300 text-[#7a1b32] focus:ring-[#7a1b32]" />
            <div className="flex-1 flex justify-between items-center">
              <span className="block text-sm font-semibold text-gray-700">Recheck ICTS setup</span>
              <span className="inline-flex items-center rounded-full bg-rose-50 px-2.5 py-0.5 text-xs font-bold text-rose-900 border border-rose-100/50 shadow-sm">High Risk</span>
            </div>
          </li>
          <li className="flex items-start gap-3 bg-white p-3 rounded-xl border border-stone-100 shadow-sm transition-shadow hover:shadow-md">
            <input type="checkbox" className="mt-1 h-4 w-4 rounded border-gray-300 text-[#7a1b32] focus:ring-[#7a1b32]" />
            <div className="flex-1 flex justify-between items-center">
              <span className="block text-sm font-semibold text-gray-700">Update participant directions</span>
              <span className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 text-xs font-bold text-amber-700 border border-amber-100/50 shadow-sm">Medium Risk</span>
            </div>
          </li>
          <li className="flex items-start gap-3 bg-white/50 p-3 rounded-xl border border-stone-100/50 opacity-75">
            <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-500" />
            <div className="flex-1 flex justify-between items-center">
              <span className="block text-sm font-semibold text-gray-500 line-through">Notify catering of new location</span>
              <span className="inline-flex items-center rounded-full bg-gray-50 px-2.5 py-0.5 text-xs font-bold text-gray-500 border border-gray-200/50 shadow-sm">Completed</span>
            </div>
          </li>
        </ul>
      </div>
    </div>
  );
}
