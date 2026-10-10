'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bell, Search, User, ChevronDown } from 'lucide-react';

export default function TopNav() {
  const pathname = usePathname();

  const links = [
    { href: '/', label: 'Home' },
    { href: '/plan', label: 'Plan Event' },
    { href: '/calendar', label: 'Calendar' },
    { href: '/venues', label: 'Venues' },
    { href: '/policy', label: 'Ask CampusCue' },
    { href: '/resources', label: 'Resources' },
  ];

  return (
    <nav className="fixed top-0 left-0 right-0 h-16 bg-[#F5EEE9]/95 backdrop-blur-md z-50 flex items-center justify-between px-6 lg:px-12 border-b border-[#F5E6DF]">
      {/* Logo Area */}
      <div className="flex items-center gap-3 w-64">
        <div className="w-9 h-9 rounded-full bg-white flex items-center justify-center shadow-sm p-1 border border-rose-100">
           <img src="https://upload.wikimedia.org/wikipedia/en/thumb/8/87/Amrita_Vishwa_Vidyapeetham_Emblem.svg/1200px-Amrita_Vishwa_Vidyapeetham_Emblem.svg.png" alt="Amrita Logo" className="w-full h-full object-contain" />
        </div>
        <div className="flex flex-col justify-center">
          <span className="text-[#7a1b32] font-serif font-bold text-lg leading-none tracking-wide">AMRITA</span>
          <span className="text-[#7a1b32] text-[8px] font-semibold tracking-widest leading-none mt-0.5 uppercase">Vishwa Vidyapeetham</span>
        </div>
      </div>

      {/* Center Links */}
      <div className="hidden md:flex items-center space-x-1">
        {links.map(link => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`px-5 py-2 text-sm font-semibold relative transition-colors ${isActive ? 'text-gray-900' : 'text-gray-600 hover:text-gray-900'}`}
            >
              {link.label}
              {isActive && (
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-8 h-[3px] bg-[#7a1b32] rounded-full" />
              )}
            </Link>
          );
        })}
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-3 w-64 justify-end">
        <button className="w-9 h-9 flex items-center justify-center text-gray-500 hover:text-gray-900 hover:bg-white rounded-full transition-colors border border-transparent hover:border-[#F5E6DF]">
          <Search className="w-4 h-4" />
        </button>
        <button className="w-9 h-9 flex items-center justify-center text-gray-500 hover:text-gray-900 hover:bg-white rounded-full transition-colors relative border border-transparent hover:border-[#F5E6DF]">
          <Bell className="w-4 h-4" />
          <span className="absolute top-2 right-2 w-2 h-2 bg-rose-500 rounded-full border-2 border-[#F5EEE9]"></span>
        </button>
        <div className="h-6 w-px bg-[#F5E6DF] mx-1"></div>
        <div className="flex items-center gap-2 cursor-pointer group hover:bg-white px-2 py-1.5 rounded-full transition-colors border border-transparent hover:border-[#F5E6DF]">
          <div className="w-8 h-8 rounded-full overflow-hidden flex items-center justify-center">
            <img src="https://images.unsplash.com/photo-1494790108377-be9c29b29330?ixlib=rb-1.2.1&auto=format&fit=crop&w=256&q=80" alt="Profile" className="w-full h-full object-cover" />
          </div>
          <div className="hidden lg:flex flex-col">
            <span className="text-xs font-bold text-gray-900 leading-tight">Hi, Mrudula!</span>
            <span className="text-[10px] text-gray-500 font-medium leading-none mt-0.5">WOMM</span>
          </div>
          <ChevronDown className="w-3 h-3 text-gray-400 ml-1" />
        </div>
      </div>
    </nav>
  );
}
