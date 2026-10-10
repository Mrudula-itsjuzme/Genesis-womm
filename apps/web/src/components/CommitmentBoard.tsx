import React from 'react';
import { Clock, CheckCircle, AlertTriangle, HelpCircle, ArrowRightCircle, CircleDashed } from 'lucide-react';

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
          <span className="inline-flex items-center gap-1.5 rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">
            <CheckCircle className="w-3.5 h-3.5" /> Confirmed
          </span>
        );
      case 'Requested':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-700/10">
            <ArrowRightCircle className="w-3.5 h-3.5" /> Requested
          </span>
        );
      case 'Pending':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-md bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-800 ring-1 ring-inset ring-yellow-600/20">
            <Clock className="w-3.5 h-3.5" /> Pending
          </span>
        );
      case 'Acknowledged':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-md bg-purple-50 px-2 py-1 text-xs font-medium text-purple-700 ring-1 ring-inset ring-purple-700/10">
            <CheckCircle className="w-3.5 h-3.5" /> Acknowledged
          </span>
        );
      case 'Needs Revalidation':
        return (
          <span className="inline-flex items-center gap-1.5 rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-600/10">
            <AlertTriangle className="w-3.5 h-3.5" /> Needs Revalidation
          </span>
        );
      case 'Not Started':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 rounded-md bg-gray-50 px-2 py-1 text-xs font-medium text-gray-600 ring-1 ring-inset ring-gray-500/10">
            <CircleDashed className="w-3.5 h-3.5" /> Not Started
          </span>
        );
    }
  };

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-800">Commitment Board</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Item</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Source / Office</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Updated</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {commitments.map((commitment, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{commitment.item}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{commitment.source}</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {getStatusBadge(commitment.status)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{commitment.lastUpdated}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
