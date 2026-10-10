import React from 'react';
import { Search, Bell, Plus, Sparkles, Command } from 'lucide-react';

export default function TopNav() {
  return (
    <header className="sticky top-4 z-30 mx-4 sm:mx-8 mb-4">
      <div className="flex h-16 items-center gap-x-4 rounded-2xl bg-white/70 backdrop-blur-md border border-white/20 shadow-[0_8px_30px_rgb(0,0,0,0.04)] px-4 sm:gap-x-6 sm:px-6">
        
        {/* Modern Search bar with AI hint */}
        <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6 items-center">
          <form className="relative flex flex-1 items-center bg-gray-50/50 hover:bg-gray-100/50 transition-colors rounded-xl px-3 py-2 border border-gray-100 focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-300 group" action="#" method="GET">
            <Search className="h-4 w-4 text-gray-400 group-focus-within:text-indigo-500 transition-colors" />
            <input
              id="search-field"
              className="block h-full w-full border-0 py-0 pl-3 pr-0 text-gray-900 placeholder:text-gray-400 focus:ring-0 sm:text-sm bg-transparent outline-none"
              placeholder="Ask Policy Assistant or search resources..."
              type="search"
              name="search"
              autoComplete="off"
            />
            <div className="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-white border border-gray-200 text-gray-500 shadow-sm">
              <Command className="w-3 h-3" />
              <span>K</span>
            </div>
          </form>
        </div>
        
        {/* Right side actions */}
        <div className="flex items-center gap-x-4 lg:gap-x-6">
          <button
            type="button"
            className="hidden sm:flex items-center gap-x-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2 text-sm font-medium text-white shadow-md shadow-indigo-500/20 hover:shadow-indigo-500/40 hover:-translate-y-0.5 transition-all focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          >
            <Sparkles className="h-4 w-4" />
            Plan Event
          </button>
          
          <div className="h-8 w-px bg-gray-200/60 hidden sm:block" />
          
          <button type="button" className="relative p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100/50 rounded-xl transition-all">
            <Bell className="h-5 w-5" />
            <span className="absolute top-2 right-2 block h-2 w-2 rounded-full bg-rose-500 ring-2 ring-white" />
          </button>

          {/* Avatar Profile */}
          <button className="flex items-center gap-x-3 p-1 rounded-xl hover:bg-gray-100/50 transition-colors">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-violet-500 to-fuchsia-500 p-[2px] shadow-sm">
              <div className="h-full w-full rounded-[10px] bg-white flex items-center justify-center">
                <span className="text-sm font-bold text-transparent bg-clip-text bg-gradient-to-tr from-violet-600 to-fuchsia-600">
                  AR
                </span>
              </div>
            </div>
          </button>
        </div>
      </div>
    </header>
  );
}
