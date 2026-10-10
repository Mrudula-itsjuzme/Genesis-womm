import React from 'react';
import { FileText, BarChart3, Download, ExternalLink } from 'lucide-react';

export default function ReportsSection() {
  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-lg font-semibold text-gray-800 mb-2">Reports</h3>
      
      <div className="bg-white rounded-lg shadow border border-gray-200 p-5 hover:border-blue-300 transition-colors cursor-pointer group">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-900 group-hover:text-blue-600">Event Summary</h4>
              <p className="text-xs text-gray-500 mt-0.5">Auto-generated attendance & highlights</p>
            </div>
          </div>
          <button className="text-gray-400 hover:text-gray-600">
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow border border-gray-200 p-5 hover:border-blue-300 transition-colors cursor-pointer group">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-50 rounded-lg text-purple-600">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-medium text-gray-900 group-hover:text-purple-600">Monthly Club Report</h4>
              <p className="text-xs text-gray-500 mt-0.5">Aggregated stats for administration</p>
            </div>
          </div>
          <button className="text-gray-400 hover:text-gray-600">
            <ExternalLink className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
