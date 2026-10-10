import React from 'react';
import { MessageSquare, FileText, Send, Sparkles } from 'lucide-react';

export const PolicyAssistant: React.FC = () => {
  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200">
      <div className="p-4 border-b border-gray-200 bg-gray-50 flex items-center">
        <Sparkles className="h-5 w-5 text-indigo-600 mr-2" />
        <h2 className="text-lg font-semibold text-gray-900">Policy Assistant</h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div className="flex justify-end">
          <div className="bg-blue-600 text-white rounded-2xl rounded-tr-none px-4 py-3 max-w-[85%] shadow-sm">
            <p className="text-sm">What do we need for an intercollege hackathon?</p>
          </div>
        </div>

        <div className="flex justify-start">
          <div className="bg-gray-100 text-gray-900 rounded-2xl rounded-tl-none px-4 py-3 max-w-[90%] shadow-sm">
            <div className="flex items-center mb-2 text-indigo-600">
              <Sparkles className="h-4 w-4 mr-1" />
              <span className="text-xs font-semibold uppercase tracking-wider">AI Assistant</span>
            </div>
            <p className="text-sm mb-3">
              Based on the current institutional guidelines, hosting an intercollege hackathon requires specific approvals and preparations:
            </p>
            <ol className="list-decimal pl-4 text-sm space-y-2 mb-3">
              <li>
                <strong>Prior Approval:</strong> You must obtain written permission from the Dean of Student Affairs at least 30 days in advance.
                <span className="inline-flex items-center ml-2 bg-white border border-gray-200 rounded px-1.5 py-0.5 text-[10px] font-medium text-gray-500 cursor-help" title="Section 4.2">
                  <FileText className="h-3 w-3 mr-1" /> OSA Handbook
                </span>
              </li>
              <li>
                <strong>Venue Booking:</strong> For intercollege events, you will likely need a major hall (like Sudhamani Hall). Note that these require a faculty sponsor signature.
              </li>
              <li>
                <strong>Security Clearance:</strong> Since external students are attending, a participant list must be submitted to Campus Security 48 hours prior.
                <span className="inline-flex items-center ml-2 bg-white border border-gray-200 rounded px-1.5 py-0.5 text-[10px] font-medium text-gray-500 cursor-help" title="Section 2.1">
                  <FileText className="h-3 w-3 mr-1" /> Security Guidelines
                </span>
              </li>
              <li>
                <strong>IT Support:</strong> Network requirements (Wi-Fi access for guests) must be coordinated with ICTS.
              </li>
            </ol>
          </div>
        </div>
      </div>

      <div className="p-4 bg-white border-t border-gray-200">
        <div className="relative rounded-lg border border-gray-300 shadow-sm focus-within:ring-1 focus-within:ring-indigo-600 focus-within:border-indigo-600">
          <textarea
            rows={2}
            className="block w-full resize-none border-0 py-2 px-3 text-gray-900 placeholder:text-gray-400 focus:ring-0 sm:text-sm sm:leading-6 bg-transparent"
            placeholder="Ask about policies, procedures, or resources..."
            defaultValue=""
          />
          <div className="absolute right-2 bottom-2">
            <button className="rounded bg-indigo-600 p-1.5 text-white hover:bg-indigo-500 shadow-sm transition-colors">
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
