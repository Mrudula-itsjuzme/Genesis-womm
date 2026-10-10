import React from 'react';
import { AlertCircle, ArrowRight, CheckCircle2 } from 'lucide-react';

export default function ChangeImpactList() {
  return (
    <div className="flex flex-col md:flex-row gap-6 mb-8">
      {/* Recent Change Card */}
      <div className="bg-white rounded-lg shadow border border-gray-200 p-5 flex-1">
        <h3 className="text-lg font-semibold mb-4 text-gray-800">Recent Change</h3>
        <div className="flex items-center gap-4 bg-gray-50 p-4 rounded-md">
          <div className="flex-1">
            <span className="block text-sm text-gray-500 mb-1">Previous</span>
            <span className="font-medium text-gray-900 line-through">Acharya Hall</span>
          </div>
          <ArrowRight className="text-gray-400 w-5 h-5" />
          <div className="flex-1">
            <span className="block text-sm text-gray-500 mb-1">Updated</span>
            <span className="font-medium text-green-700">Seminar Hall II</span>
          </div>
        </div>
      </div>

      {/* Change Impact Checklist */}
      <div className="bg-white rounded-lg shadow border border-gray-200 p-5 flex-1">
        <h3 className="text-lg font-semibold mb-4 text-gray-800 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-amber-500" />
          Change Impact
        </h3>
        <ul className="space-y-3">
          <li className="flex items-start gap-3">
            <input type="checkbox" className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
            <div className="flex-1">
              <span className="block text-sm font-medium text-gray-700">Recheck ICTS setup</span>
              <span className="inline-flex items-center rounded-full bg-red-50 px-2 py-1 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-600/10 mt-1">High Risk</span>
            </div>
          </li>
          <li className="flex items-start gap-3">
            <input type="checkbox" className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
            <div className="flex-1">
              <span className="block text-sm font-medium text-gray-700">Update participant directions</span>
              <span className="inline-flex items-center rounded-full bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-800 ring-1 ring-inset ring-yellow-600/20 mt-1">Medium Risk</span>
            </div>
          </li>
          <li className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-5 w-5 text-green-500" />
            <div className="flex-1">
              <span className="block text-sm font-medium text-gray-500 line-through">Notify catering of new location</span>
              <span className="inline-flex items-center rounded-full bg-gray-50 px-2 py-1 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-500/10 mt-1">Completed</span>
            </div>
          </li>
        </ul>
      </div>
    </div>
  );
}
