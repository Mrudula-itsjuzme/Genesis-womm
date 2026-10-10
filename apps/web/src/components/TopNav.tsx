import React from 'react';
import Link from 'next/link';
import { Search, Bell, User, ChevronDown } from 'lucide-react';

export default function TopNav() {
  return (
    <header className="sticky top-0 z-50 flex h-20 items-center justify-between border-b border-rose-100 bg-white px-6 shadow-sm">
      
      {/* Left: Logo */}
      <div className="flex items-center gap-3">
        {/* Placeholder for Amrita Logo */}
        <div className="flex items-center justify-center w-10 h-10 rounded-full bg-rose-900 text-white font-bold text-xl shadow-inner">
          A
        </div>
        <div className="flex flex-col">
          <span className="text-xl font-bold text-rose-900 leading-tight">AMRITA</span>
          <span className="text-[0.6rem] font-semibold text-rose-700 tracking-widest uppercase">Vishwa Vidyapeetham</span>
        </div>
      </div>

      {/* Center: Navigation Links */}
      <nav className="hidden lg:flex items-center gap-2">
        <Link href="/" className="px-5 py-2 rounded-full bg-rose-50 text-rose-900 font-semibold text-sm transition-colors">
          Home
        </Link>
        <Link href="/plan" className="px-5 py-2 rounded-full text-gray-700 hover:bg-gray-50 font-medium text-sm transition-colors">
          Plan Event
        </Link>
        <Link href="/calendar" className="px-5 py-2 rounded-full text-gray-700 hover:bg-gray-50 font-medium text-sm transition-colors">
          Calendar
        </Link>
        <Link href="/venues" className="px-5 py-2 rounded-full text-gray-700 hover:bg-gray-50 font-medium text-sm transition-colors">
          Venues
        </Link>
        <Link href="/policy" className="px-5 py-2 rounded-full text-gray-700 hover:bg-gray-50 font-medium text-sm transition-colors">
          Ask CampusCue
        </Link>
        <Link href="/resources" className="px-5 py-2 rounded-full text-gray-700 hover:bg-gray-50 font-medium text-sm transition-colors">
          Resources
        </Link>
      </nav>

      {/* Right: Actions & Profile */}
      <div className="flex items-center gap-x-4">
        
        {/* Search Icon Button */}
        <button type="button" className="p-2 rounded-full border border-gray-200 text-gray-500 hover:bg-gray-50 transition-colors">
          <span className="sr-only">Search</span>
          <Search className="h-5 w-5" aria-hidden="true" />
        </button>
        
        {/* Notification Bell */}
        <button type="button" className="relative p-2 rounded-full border border-gray-200 text-gray-500 hover:bg-gray-50 transition-colors">
          <span className="sr-only">View notifications</span>
          <Bell className="h-5 w-5" aria-hidden="true" />
          <span className="absolute top-0 right-0 block h-2.5 w-2.5 rounded-full bg-rose-600 ring-2 ring-white" />
        </button>

        {/* User Profile */}
        <button className="flex items-center gap-x-3 hover:bg-gray-50 p-1.5 rounded-full transition-colors border border-transparent hover:border-gray-200">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-rose-100 text-rose-800 overflow-hidden shadow-sm">
            {/* Real photo could go here, using an icon as fallback */}
            <User className="h-6 w-6 text-rose-700 mt-1" />
          </div>
          <div className="hidden md:flex flex-col items-start pr-2">
            <span className="text-sm font-bold text-gray-900 leading-tight">Hi, Mrudula!</span>
            <span className="text-xs text-gray-500 font-medium">WOMM <ChevronDown className="inline w-3 h-3 ml-1" /></span>
          </div>
        </button>
      </div>
    </header>
  );
}
