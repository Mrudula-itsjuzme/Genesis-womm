'use client';
import { useAuth } from '@/context/AuthContext';
import CalendarGrid from '@/components/CalendarGrid';
import Link from 'next/link';
import UpcomingEvents from "@/components/UpcomingEvents";
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
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,1.45fr)_minmax(300px,0.85fr)] lg:gap-12 items-start">

          {/* My Events List */}
          <section className="min-w-0 border-t border-[#d9c9c2] py-6 lg:border-t-0 lg:py-0" aria-labelledby="upcoming-events-heading">
            <div className="mb-6 flex items-center justify-between gap-3">
              <h3 id="upcoming-events-heading" className="text-xl font-bold tracking-tight text-gray-900">My Upcoming Events</h3>
              <Link href="/calendar" className="flex items-center text-xs font-bold uppercase tracking-wider text-[#7a1b32] transition-colors hover:text-rose-900">
                View Calendar <ArrowRight className="ml-1 h-3 w-3" />
              </Link>
            </div>

            <UpcomingEvents />
          </section>

          {/* Campus Calendar */}
          <section className="min-w-0 border-t border-[#d9c9c2] py-6 lg:border-t-0 lg:py-0" aria-labelledby="campus-calendar-heading">
            <div className="mb-6 flex items-center justify-between gap-3">
              <h3 id="campus-calendar-heading" className="text-lg font-bold tracking-tight text-gray-900">Campus Calendar</h3>
              <Link href="/plan" className="flex items-center gap-1 rounded-full bg-[#7a1b32] px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide text-white transition-colors hover:bg-[#5a1122]">
                <Plus className="w-3 h-3" /> New Event
              </Link>
            </div>

            <CalendarGrid />
          </section>
        </div>

        {/* Row 2: Ask CampusCue · Promo */}
        <div className="grid grid-cols-1 lg:grid-cols-[19fr_10fr] gap-6 items-stretch mt-6">
          {/* Ask CampusCue Banner */}
          <div className="bg-gradient-to-r from-[#FDE8E9] via-[#F6DCE0] to-[#EED3D9] rounded-3xl p-8 border-none relative overflow-hidden flex items-center shadow-sm h-56">

            <div className="relative z-10 w-full pr-12">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-6 h-6 text-[#7a1b32]" />
                <h3 className="text-2xl font-serif font-bold text-[#7a1b32]">Ask CampusCue</h3>
              </div>
              <p className="text-sm text-[#7a1b32]/80 mb-6 font-medium">Get answers from Amrita&apos;s official guidelines, venue details, and past events.</p>

              <Link href="/policy" className="inline-block rounded-full bg-white px-6 py-3 text-[#7a1b32]">Open policy assistant</Link>
            </div>
          </div>

          {/* Promo block */}
          <div className="bg-white rounded-3xl p-6 relative overflow-hidden h-56 flex items-center shadow-sm border-none">
            <div className="absolute inset-0 z-0 bg-cover bg-center" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1541339907198-e08756dedf3f?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80')" }}></div>
            <div className="absolute inset-0 bg-gradient-to-t from-white/95 via-white/80 to-transparent z-0" />
            <div className="absolute inset-0 bg-gradient-to-l from-[#F5EEE9]/95 via-[#F5EEE9]/80 to-transparent z-0" />
            <div className="relative z-10 flex-1 flex flex-col justify-center items-end pr-4 mt-12">
              <p className="text-[#7a1b32] font-serif text-xl leading-snug text-right max-w-[150px] drop-shadow-sm font-bold">
                Events build the campus we remember.
              </p>
              <div className="w-12 h-1 bg-[#7a1b32] mt-4 rounded-full opacity-50"></div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
