import React from 'react';
import { Search, Bell, Plus, User, ChevronDown } from 'lucide-react';

export default function TopNav() {
  return (
    <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-gray-200 bg-white px-4 sm:px-6 lg:px-8">
      
      {/* Left: Search Bar */}
      <div className="flex flex-1 max-w-2xl">
        <div className="relative w-full">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
            <Search className="h-5 w-5 text-gray-400" aria-hidden="true" />
          </div>
          <input
            type="search"
            name="search"
            id="search"
            className="block w-full rounded-lg border border-gray-200 bg-gray-50 py-2.5 pl-10 pr-3 text-sm placeholder-gray-500 focus:border-rose-800 focus:bg-white focus:outline-none focus:ring-1 focus:ring-rose-800 transition-colors"
            placeholder="Search events, venues, or policies"
          />
        </div>
      </div>

      {/* Right: Actions & Profile */}
      <div className="flex items-center gap-x-6 ml-4">
        
        {/* New Event Button */}
        <button
          type="button"
          className="inline-flex items-center gap-x-2 rounded-lg bg-rose-800 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-rose-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-800 transition-colors"
        >
          New Event
          <Plus className="-mr-0.5 h-4 w-4" aria-hidden="true" />
        </button>
        
        {/* Notification Bell */}
        <button type="button" className="relative p-1 text-gray-500 hover:text-gray-700">
          <span className="sr-only">View notifications</span>
          <Bell className="h-6 w-6" aria-hidden="true" />
          <span className="absolute top-1 right-1.5 block h-2.5 w-2.5 rounded-full bg-amber-500 ring-2 ring-white" />
        </button>

        {/* User Profile */}
        <button className="flex items-center gap-x-3 hover:bg-gray-50 p-1.5 rounded-lg transition-colors">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-rose-100 text-rose-800">
            <User className="h-5 w-5" />
          </div>
          <div className="hidden md:flex md:items-center md:gap-x-1">
            <span className="text-sm font-medium text-gray-700">Arjun Admin</span>
            <ChevronDown className="h-4 w-4 text-gray-500" aria-hidden="true" />
          </div>
        </button>

      </div>
    </header>
  );
}
