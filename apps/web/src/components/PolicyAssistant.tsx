import React from 'react';
import { MessageSquare, FileText, Send, Sparkles } from 'lucide-react';

export const PolicyAssistant: React.FC = () => {
  return (
    <div className="flex flex-col h-full bg-transparent">
      <div className="px-6 py-5 border-b border-rose-100/30 bg-white/40 flex items-center shadow-sm">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#7a1b32] to-[#5a1222] flex items-center justify-center mr-3 shadow-md">
          <Sparkles className="h-4 w-4 text-white" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-gray-900 tracking-tight">Policy Assistant</h2>
          <p className="text-[10px] uppercase tracking-wider font-bold text-[#7a1b32]">AI Powered</p>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="flex justify-end">
          <div className="bg-gradient-to-br from-[#7a1b32] to-[#5a1222] text-white rounded-2xl rounded-tr-none px-5 py-4 max-w-[85%] shadow-md">
            <p className="text-sm font-medium leading-relaxed">What do we need for an intercollege hackathon?</p>
          </div>
        </div>

        <div className="flex justify-start">
          <div className="bg-white text-gray-800 rounded-2xl rounded-tl-none px-5 py-4 max-w-[95%] shadow-[0_4px_20px_rgb(0,0,0,0.04)] border border-stone-100/50">
            <div className="flex items-center mb-3 text-[#7a1b32]">
              <Sparkles className="h-4 w-4 mr-1.5" />
              <span className="text-[10px] font-bold uppercase tracking-wider">CampusCue Assistant</span>
            </div>
            <p className="text-sm mb-4 leading-relaxed font-medium">
              Based on the current institutional guidelines, hosting an intercollege hackathon requires specific approvals and preparations:
            </p>
            <ol className="list-decimal pl-4 text-sm space-y-3 mb-2 font-medium">
              <li className="pl-1">
                <strong className="text-gray-900">Prior Approval:</strong> You must obtain written permission from the Dean of Student Affairs at least 30 days in advance.
                <span className="inline-flex items-center ml-2 bg-[#FFF5F0] border border-rose-100 rounded-full px-2 py-0.5 text-[10px] font-bold text-[#7a1b32] cursor-help shadow-sm uppercase tracking-wider mt-1" title="Section 4.2">
                  <FileText className="h-3 w-3 mr-1" /> OSA Handbook
                </span>
              </li>
              <li className="pl-1">
                <strong className="text-gray-900">Venue Booking:</strong> For intercollege events, you will likely need a major hall (like Sudhamani Hall). Note that these require a faculty sponsor signature.
              </li>
              <li className="pl-1">
                <strong className="text-gray-900">Security Clearance:</strong> Since external students are attending, a participant list must be submitted to Campus Security 48 hours prior.
                <span className="inline-flex items-center ml-2 bg-[#FFF5F0] border border-rose-100 rounded-full px-2 py-0.5 text-[10px] font-bold text-[#7a1b32] cursor-help shadow-sm uppercase tracking-wider mt-1" title="Section 2.1">
                  <FileText className="h-3 w-3 mr-1" /> Security Guidelines
                </span>
              </li>
              <li className="pl-1">
                <strong className="text-gray-900">IT Support:</strong> Network requirements (Wi-Fi access for guests) must be coordinated with ICTS.
              </li>
            </ol>
          </div>
        </div>
      </div>

      <div className="p-6 bg-white/60 border-t border-rose-100/30 backdrop-blur-md">
        <div className="relative bg-white rounded-2xl shadow-[0_4px_20px_rgb(0,0,0,0.04)] focus-within:ring-2 focus-within:ring-rose-500/20 focus-within:shadow-md transition-all">
          <textarea
            rows={2}
            className="block w-full resize-none border-none py-4 px-4 text-gray-900 placeholder:text-gray-400 focus:ring-0 sm:text-sm sm:leading-6 bg-transparent font-medium rounded-2xl"
            placeholder="Ask about policies, procedures, or resources..."
            defaultValue=""
          />
          <div className="absolute right-3 bottom-3">
            <button className="rounded-xl bg-[#7a1b32] p-2 text-white hover:bg-[#5a1222] shadow-md transition-transform hover:scale-105 active:scale-95">
              <Send className="h-4 w-4 ml-0.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
