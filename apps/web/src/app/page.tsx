'use client';
import { useAuth } from '@/context/AuthContext';
import CalendarGrid from '@/components/CalendarGrid';
import Link from 'next/link';
import UpcomingEvents from "@/components/UpcomingEvents";
import { PolicyAssistant } from '@/components/PolicyAssistant';
import { Calendar, MapPin, FileText, BarChart2, Plus, ArrowRight, Sparkles } from 'lucide-react';

export default function Dashboard() {
  const { session } = useAuth();
  return (
    <div className="min-h-screen font-sans bg-[#F5EEE9]">
      {/* Hero Section */}
      <section className="relative w-full h-[400px] overflow-hidden flex flex-col justify-center px-8 md:px-16 lg:px-24 rounded-b-[40px]">
        {/* Background Image Placeholder */}
        <div
          className="absolute inset-0 z-0"
          style={{
            backgroundImage: "url('https://upload.wikimedia.org/wikipedia/commons/2/2c/Amrita_Vishwa_Vidyapeetham_coimbatore_campus.jpg')",
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundRepeat: 'no-repeat',
            filter: "brightness(0.75) contrast(1.1)"
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[#3e131d]/70 via-[#4a1723]/30 to-transparent z-0" />

        <div className="relative z-10 text-gray-900 mt-16 max-w-4xl drop-shadow-sm">
          <h2 className="text-xl md:text-2xl font-serif italic font-light mb-1 text-white drop-shadow-md">Welcome,</h2>
          <h1 className="text-5xl md:text-7xl font-serif mb-3 text-white drop-shadow-md tracking-tight">{session?.user.display_name ?? 'CampusCue'}</h1>
          <p className="text-lg md:text-xl font-light mb-8 text-white/90 drop-shadow-md tracking-wide">Let&apos;s make something happen on campus.</p>

          <Link href="/policy" className="inline-block rounded-full bg-white px-6 py-3 text-[#7a1b32]">Ask a campus question</Link>
        </div>

        {/* Right side floating text */}
        <div className="absolute right-16 top-1/2 -translate-y-1/2 mt-8 hidden lg:block z-10 text-right">
          <p className="text-white text-xl font-light tracking-wide leading-relaxed drop-shadow-md opacity-90 border-r-2 border-rose-200/50 pr-5">
            Same<br />campus.<br />New<br />possibilities.
          </p>
        </div>
      </section>

      {/* Main Content Area */}
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12 -mt-12 relative z-20 pb-20">

        {/* Action Cards Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-10">

          {/* Card 1 */}
          <Link href="/plan" className="block bg-gradient-to-br from-[#7a1b32] to-[#4a0d1b] rounded-3xl p-6 text-white shadow-xl hover:shadow-2xl hover:-translate-y-1 transition-all h-44 cursor-pointer relative z-30 overflow-hidden">
            <div className="absolute right-0 top-0 bottom-0 opacity-20 transform translate-x-4">
              <Calendar className="w-40 h-full" strokeWidth={1} />
            </div>
            <div className="relative z-10 h-full flex flex-col justify-between group">
              <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-2 bg-white/10 backdrop-blur-sm border border-white/10">
                <Calendar className="w-6 h-6 text-white" />
              </div>
              <div className="pr-12">
                <h3 className="text-lg font-bold mb-1 tracking-tight">Plan an Event</h3>
                <p className="text-xs text-rose-100 leading-relaxed max-w-[90%]">Find a date, check availability and get started</p>
              </div>
              <div className="absolute bottom-5 right-5 w-8 h-8 rounded-full bg-white text-[#7a1b32] flex items-center justify-center shadow-md group-hover:scale-110 transition-transform">
                <ArrowRight className="w-4 h-4" />
              </div>
            </div>
          </Link>

          {/* Card 2 */}
          <Link href="/venues" className="block bg-white border border-white/60 rounded-3xl p-6 text-gray-800 shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all h-44 relative overflow-hidden cursor-pointer z-30">
            <div className="relative z-10 h-full flex flex-col justify-between group">
              <div className="w-12 h-12 rounded-xl bg-white shadow-sm flex items-center justify-center mb-2 border border-rose-50">
                <MapPin className="w-6 h-6 text-[#7a1b32]" />
              </div>
              <div className="pr-12">
                <h3 className="text-lg font-bold mb-1 text-gray-900 tracking-tight">Explore Venues</h3>
                <p className="text-xs text-gray-500 leading-relaxed max-w-[90%] font-medium">View halls, classrooms, labs and open spaces</p>
              </div>
              <div className="absolute bottom-5 right-5 w-8 h-8 rounded-full bg-white text-gray-700 flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
                <ArrowRight className="w-4 h-4" />
              </div>
            </div>
          </Link>

          {/* Card 3 */}
          <Link href="/policy" className="block bg-white border border-white/60 rounded-3xl p-6 text-gray-800 shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all h-44 relative overflow-hidden cursor-pointer z-30">
            <div className="relative z-10 h-full flex flex-col justify-between group">
              <div className="w-12 h-12 rounded-xl bg-white shadow-sm flex items-center justify-center mb-2 border border-rose-50">
                <FileText className="w-6 h-6 text-[#7a1b32]" />
              </div>
              <div className="pr-12">
                <h3 className="text-lg font-bold mb-1 text-gray-900 tracking-tight">Ask a Policy Question</h3>
                <p className="text-xs text-gray-500 leading-relaxed max-w-[90%] font-medium">Get instant answers from OSA guidelines</p>
              </div>
              <div className="absolute bottom-5 right-5 w-8 h-8 rounded-full bg-white text-gray-700 flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
                <ArrowRight className="w-4 h-4" />
              </div>
            </div>
          </Link>

          {/* Card 4 */}
          <Link href="/changes" className="block bg-white border border-white/60 rounded-3xl p-6 text-gray-800 shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all h-44 relative overflow-hidden cursor-pointer z-30">
            <div className="absolute right-0 top-0 bottom-0 w-1/2">
              <div
                className="absolute inset-0 z-0 mix-blend-multiply opacity-20"
                style={{
                  backgroundImage: "url('https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=600&q=80')",
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                  backgroundRepeat: 'no-repeat'
                }}
              />
              <div className="absolute inset-0 bg-gradient-to-r from-[#FFF4ED] to-transparent z-0" />
            </div>
            <div className="relative z-10 h-full flex flex-col justify-between group">
              <div className="w-12 h-12 rounded-xl bg-white shadow-sm flex items-center justify-center mb-2 border border-rose-50">
                <BarChart2 className="w-6 h-6 text-[#7a1b32]" />
              </div>
              <div className="pr-12">
                <h3 className="text-lg font-bold mb-1 text-gray-900 tracking-tight">See Change Impact</h3>
                <p className="text-xs text-gray-500 leading-relaxed max-w-[90%] font-medium">Understand how changes affect other events</p>
              </div>
              <div className="absolute bottom-5 right-5 w-8 h-8 rounded-full bg-white text-gray-700 flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
                <ArrowRight className="w-4 h-4" />
              </div>
            </div>
          </Link>
        </div>

        {/* Dashboard Grid Content */}
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2 items-start mb-8">
          {/* My Events List */}
          <section className="space-y-4 min-w-0" aria-labelledby="upcoming-events-heading">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h3 id="upcoming-events-heading" className="text-xl font-bold tracking-tight text-gray-900">
                  My Upcoming Events
                </h3>
                <p className="text-xs text-stone-500 mt-0.5">
                  Track tentative proposals, confirmed bookings, and event changes.
                </p>
              </div>
              <Link href="/calendar" className="flex items-center text-xs font-bold uppercase tracking-wider text-[#7a1b32] transition-colors hover:text-rose-900">
                View Calendar <ArrowRight className="ml-1 h-3 w-3" />
              </Link>
            </div>
            <UpcomingEvents />
          </section>

          {/* Ask CampusCue Live Assistant */}
          <section className="space-y-4 min-w-0" aria-labelledby="policy-assistant-heading">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h3 id="policy-assistant-heading" className="text-xl font-bold tracking-tight text-gray-900">
                  Ask CampusCue
                </h3>
                <p className="text-xs text-stone-500 mt-0.5">
                  Policy-grounded assistant for event permissions, venues, and student affairs rules.
                </p>
              </div>
              <Link href="/policy" className="flex items-center text-xs font-bold uppercase tracking-wider text-[#7a1b32] transition-colors hover:text-rose-900">
                Full Page <ArrowRight className="ml-1 h-3 w-3" />
              </Link>
            </div>
            <PolicyAssistant />
            <div className="bg-white rounded-[10px] p-4 shadow-xs border border-stone-200/80 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-stone-400">Institutional Operations</p>
                <p className="text-xs font-semibold text-stone-800 mt-0.5">Need to review event changes or resolve conflict impact?</p>
              </div>
              <Link href="/changes" className="rounded-[8px] border border-stone-200 bg-stone-50 px-3.5 py-1.5 text-xs font-semibold text-[#7a1b32] transition hover:bg-rose-50 active:scale-[0.98]">
                Review Changes →
              </Link>
            </div>
          </section>
        </div>

        {/* Campus Calendar: Full Width Dedicated Showcase */}
        <section className="rounded-[10px] border border-stone-200/80 bg-white/95 p-6 shadow-sm backdrop-blur-xl" aria-labelledby="campus-calendar-heading">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-stone-100 pb-3">
            <div>
              <h3 id="campus-calendar-heading" className="text-xl font-bold tracking-tight text-gray-900">Campus Master Calendar</h3>
              <p className="text-xs text-stone-500 mt-0.5">Comprehensive schedule of institutional bookings, proposals, and club workshops.</p>
            </div>
            <div className="flex items-center gap-3">
              <Link href="/plan" className="flex items-center gap-1 rounded-[10px] bg-[#7a1b32] px-3.5 py-1.5 text-xs font-semibold text-white shadow-xs transition-all duration-150 hover:bg-[#5a1122] active:scale-[0.98]">
                <Plus className="w-3 h-3" /> New Event
              </Link>
            </div>
          </div>

          <CalendarGrid />
        </section>
      </div>
    </div>
  );
}
