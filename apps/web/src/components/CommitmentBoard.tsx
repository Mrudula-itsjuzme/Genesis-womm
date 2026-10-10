import React from 'react';
import { Clock, CheckCircle, AlertTriangle, ArrowRightCircle, CircleDashed } from 'lucide-react';

export default function CommitmentBoard() {
  const commitments = [
    { item: 'Venue Approval', source: 'Estate Office', status: 'Confirmed', lastUpdated: 'Today, 10:30 AM' },
    { item: 'ICTS Setup', source: 'IT Department', status: 'Requested', lastUpdated: 'Yesterday, 2:15 PM' },
    { item: 'Catering Options', source: 'Food Services', status: 'Pending', lastUpdated: '2 Days ago' },
    { item: 'Security Clearance', source: 'Campus Security', status: 'Acknowledged', lastUpdated: 'Today, 9:00 AM' },
    { item: 'Guest Speaker Travel', source: 'Admin Coordinator', status: 'Needs Revalidation', lastUpdated: '1 Hr ago' },
    { item: 'Post-Event Cleanup', source: 'Housekeeping', status: 'Not Started', lastUpdated: '--' },
  ];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'Confirmed':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700 border border-emerald-100 shadow-sm">
            <CheckCircle className="w-3.5 h-3.5" /> Confirmed
          </span>
        );
      case 'Requested':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700 border border-blue-100 shadow-sm">
            <ArrowRightCircle className="w-3.5 h-3.5" /> Requested
          </span>
        );
      case 'Pending':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-2.5 py-1 text-xs font-bold text-amber-700 border border-amber-100 shadow-sm">
            <Clock className="w-3.5 h-3.5" /> Pending
          </span>
        );
      case 'Acknowledged':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-bold text-indigo-700 border border-indigo-100 shadow-sm">
            <CheckCircle className="w-3.5 h-3.5" /> Acknowledged
          </span>
        );
      case 'Needs Revalidation':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-50 px-2.5 py-1 text-xs font-bold text-rose-800 border border-rose-200 shadow-sm">
            <AlertTriangle className="w-3.5 h-3.5" /> Needs Revalidation
          </span>
        );
      case 'Not Started':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-stone-100 px-2.5 py-1 text-xs font-bold text-stone-600 border border-stone-200 shadow-sm">
            <CircleDashed className="w-3.5 h-3.5" /> Not Started
          </span>
        );
    }
  };

  return (
    <div className="bg-[#FAF9F8] rounded-2xl shadow-sm border border-stone-200/50 overflow-hidden">
      <div className="px-6 py-5 border-b border-stone-200/50 bg-white/50">
        <h3 className="text-lg font-bold text-gray-900">Commitment Board</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-stone-200/50">
          <thead className="bg-stone-50/50">
            <tr>
              <th scope="col" className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Item</th>
              <th scope="col" className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Source / Office</th>
              <th scope="col" className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Status</th>
              <th scope="col" className="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Last Updated</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-stone-100">
            {commitments.map((commitment, idx) => (
              <tr key={idx} className="hover:bg-stone-50/50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">{commitment.item}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-500">{commitment.source}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getStatusBadge(commitment.status)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-400">{commitment.lastUpdated}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
