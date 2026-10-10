import React from 'react';
import { FileText, BarChart3, Download, ExternalLink } from 'lucide-react';

export default function ReportsSection() {
  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-lg font-bold text-gray-900 mb-2">Reports</h3>
      
      <div className="bg-[#FAF9F8] rounded-2xl shadow-sm border border-stone-200/50 p-5 hover:border-rose-200 hover:shadow-md transition-all cursor-pointer group relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-rose-100/50 to-transparent rounded-full -mr-16 -mt-16 z-0 mix-blend-multiply transition-transform group-hover:scale-110"></div>
        <div className="relative z-10 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-white shadow-sm rounded-xl text-[#7a1b32] border border-stone-100">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-gray-900 group-hover:text-[#7a1b32] transition-colors">Event Summary</h4>
              <p className="text-xs font-medium text-gray-500 mt-0.5">Auto-generated attendance & highlights</p>
            </div>
          </div>
          <button className="text-gray-400 hover:text-[#7a1b32] transition-colors p-1">
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="bg-[#FAF9F8] rounded-2xl shadow-sm border border-stone-200/50 p-5 hover:border-indigo-200 hover:shadow-md transition-all cursor-pointer group relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-indigo-100/50 to-transparent rounded-full -mr-16 -mt-16 z-0 mix-blend-multiply transition-transform group-hover:scale-110"></div>
        <div className="relative z-10 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-white shadow-sm rounded-xl text-indigo-700 border border-stone-100">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-gray-900 group-hover:text-indigo-700 transition-colors">Monthly Club Report</h4>
              <p className="text-xs font-medium text-gray-500 mt-0.5">Aggregated stats for administration</p>
            </div>
          </div>
          <button className="text-gray-400 hover:text-indigo-700 transition-colors p-1">
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
