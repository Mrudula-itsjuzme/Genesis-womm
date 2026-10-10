import React from 'react';
import Link from 'next/link';
import UpcomingEvents from "@/components/UpcomingEvents";
import { Calendar, Search, MapPin, FileText, BarChart2, Plus, ArrowRight, Phone, HeartPulse, Send, Book, Sparkles, Clock } from 'lucide-react';

export default function Dashboard() {
  return (
    <div className="min-h-screen font-sans" style={{ backgroundColor: '#FAF9F8' }}>
      {/* Hero Section */}
      <section className="relative w-full h-[450px] overflow-hidden flex flex-col justify-center px-8 md:px-16 lg:px-24">
        {/* Background Image Placeholder */}
        <div 
          className="absolute inset-0 z-0"
          style={{ 
            backgroundImage: "url('https://upload.wikimedia.org/wikipedia/commons/2/2c/Amrita_Vishwa_Vidyapeetham_coimbatore_campus.jpg')",
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundRepeat: 'no-repeat',
            filter: "brightness(0.8)"
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[#FAF9F8]/80 via-[#FAF9F8]/40 to-transparent z-0" />
        
        <div className="relative z-10 text-gray-900 mt-12 max-w-4xl drop-shadow-sm">
          <h2 className="text-xl md:text-2xl font-light mb-1 text-white drop-shadow-md">Good evening,</h2>
          <h1 className="text-5xl md:text-7xl font-serif mb-4 text-white drop-shadow-md">Mrudula</h1>
          <p className="text-lg md:text-xl font-light mb-10 text-white/90 drop-shadow-md">Let&apos;s make something happen on campus.</p>
          
          {/* Main Search Bar */}
          <div className="relative max-w-2xl bg-white backdrop-blur-md rounded-full shadow-lg flex items-center px-5 py-3.5 border border-gray-100 transition-all focus-within:ring-4 focus-within:ring-rose-500/20">
            <Search className="w-5 h-5 text-gray-500 mr-3" />
            <input 
              type="text" 
              placeholder="Search for venues, events, policies, or ask anything..." 
              className="flex-1 bg-transparent border-none focus:ring-0 text-gray-800 placeholder-gray-400 text-sm md:text-base outline-none"
            />
            <div className="hidden sm:flex items-center space-x-1 text-xs text-gray-400 font-mono px-2">
              <kbd className="px-2 py-1 rounded bg-gray-50 border border-gray-200">Ctrl</kbd>
              <kbd className="px-2 py-1 rounded bg-gray-50 border border-gray-200">K</kbd>
            </div>
          </div>
        </div>

        {/* Right side floating text */}
        <div className="absolute right-12 top-1/2 -translate-y-1/2 hidden lg:block z-10 text-right">
          <p className="text-white text-lg font-light tracking-wide leading-relaxed drop-shadow-md opacity-90 border-r-2 border-white/50 pr-4">
            Same<br/>campus.<br/>New<br/>possibilities.
          </p>
        </div>
      </section>

      {/* Main Content Area */}
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12 -mt-16 relative z-20 pb-20">
        
        {/* Action Cards Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          
          {/* Card 1 */}
          <Link href="/plan" className="block bg-gradient-to-r from-[#7a1b32] to-[#5a1222] rounded-[24px] p-6 text-white shadow-xl hover:shadow-2xl hover:-translate-y-1 transition-all h-44 cursor-pointer relative z-30 overflow-hidden">
            <div className="absolute right-0 top-0 bottom-0 opacity-20 transform translate-x-4">
              <Calendar className="w-40 h-full" strokeWidth={1} />
            </div>
            <div className="relative z-10 h-full flex flex-col justify-between group">
              <div className="w-12 h-12 rounded-xl border border-white/20 flex items-center justify-center mb-2 bg-white/5 backdrop-blur-sm">
                <Calendar className="w-6 h-6 text-white" />
              </div>
              <div className="pr-12">
                <h3 className="text-xl font-bold mb-1">Plan an Event</h3>
                <p className="text-xs text-white/80 leading-relaxed max-w-[90%]">Find a date, check availability and get started</p>
              </div>
              <div className="absolute bottom-6 right-6 w-8 h-8 rounded-full bg-white text-[#7a1b32] flex items-center justify-center shadow-md group-hover:scale-110 transition-transform">
                <ArrowRight className="w-4 h-4" />
              </div>
            </div>
          </Link>

          {/* Card 2 */}
          <Link href="/venues" className="block bg-[#FAF6F3] border border-[#f0e6dd] rounded-[24px] p-6 text-gray-800 shadow-md hover:shadow-xl hover:-translate-y-1 transition-all h-44 relative overflow-hidden cursor-pointer z-30">
            <div className="absolute right-0 top-0 bottom-0 w-1/2">
              <div 
                className="absolute inset-0 z-0 mix-blend-multiply opacity-30 transition-transform group-hover:scale-105 duration-700"
                style={{ 
                  backgroundImage: "url('https://images.unsplash.com/photo-1590457635677-7871b6d05f3b?auto=format&fit=crop&w=600&q=80')",
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                  backgroundRepeat: 'no-repeat'
                }}
              />
              <div className="absolute inset-0 bg-gradient-to-r from-[#FAF6F3] to-transparent z-0" />
            </div>
            <div className="relative z-10 h-full flex flex-col justify-between group">
              <div className="w-12 h-12 rounded-xl bg-white shadow-sm flex items-center justify-center mb-2">
                <MapPin className="w-6 h-6 text-[#7a1b32]" />
              </div>
              <div className="pr-12">
                <h3 className="text-xl font-bold mb-1 text-gray-900">Explore Venues</h3>
                <p className="text-xs text-stone-500 leading-relaxed max-w-[90%] font-medium">View halls, classrooms, labs and open spaces</p>
              </div>
              <div className="absolute bottom-6 right-6 w-8 h-8 rounded-full bg-white text-gray-700 border border-gray-100 flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
                <ArrowRight className="w-4 h-4" />
              </div>
            </div>
          </Link>

          {/* Card 3 */}
          <Link href="/policy" className="block bg-[#FAF6F3] border border-[#f0e6dd] rounded-[24px] p-6 text-gray-800 shadow-md hover:shadow-xl hover:-translate-y-1 transition-all h-44 relative overflow-hidden cursor-pointer z-30">
            <div className="absolute right-0 top-0 bottom-0 w-1/2">
              <div 
                className="absolute inset-0 z-0 mix-blend-multiply opacity-30 transition-transform group-hover:scale-105 duration-700"
                style={{ 
                  backgroundImage: "url('https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?auto=format&fit=crop&w=600&q=80')",
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                  backgroundRepeat: 'no-repeat'
                }}
              />
              <div className="absolute inset-0 bg-gradient-to-r from-[#FAF6F3] to-transparent z-0" />
            </div>
            <div className="relative z-10 h-full flex flex-col justify-between group">
              <div className="w-12 h-12 rounded-xl bg-white shadow-sm flex items-center justify-center mb-2">
                <FileText className="w-6 h-6 text-[#7a1b32]" />
              </div>
              <div className="pr-12">
                <h3 className="text-xl font-bold mb-1 text-gray-900">Ask a Policy Question</h3>
                <p className="text-xs text-stone-500 leading-relaxed max-w-[90%] font-medium">Get instant answers from OSA guidelines</p>
              </div>
              <div className="absolute bottom-6 right-6 w-8 h-8 rounded-full bg-white text-gray-700 border border-gray-100 flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
                <ArrowRight className="w-4 h-4" />
              </div>
            </div>
          </Link>

          {/* Card 4 */}
          <Link href="/changes" className="block bg-[#FAF6F3] border border-[#f0e6dd] rounded-[24px] p-6 text-gray-800 shadow-md hover:shadow-xl hover:-translate-y-1 transition-all h-44 relative overflow-hidden cursor-pointer z-30">
             <div className="absolute right-0 top-0 bottom-0 w-1/2">
              <div 
                className="absolute inset-0 z-0 mix-blend-multiply opacity-30 transition-transform group-hover:scale-105 duration-700"
                style={{ 
                  backgroundImage: "url('https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=600&q=80')",
                  backgroundSize: 'cover',
                  backgroundPosition: 'center',
                  backgroundRepeat: 'no-repeat'
                }}
              />
              <div className="absolute inset-0 bg-gradient-to-r from-[#FAF6F3] to-transparent z-0" />
            </div>
            <div className="relative z-10 h-full flex flex-col justify-between group">
              <div className="w-12 h-12 rounded-xl bg-white shadow-sm flex items-center justify-center mb-2">
                <BarChart2 className="w-6 h-6 text-[#7a1b32]" />
              </div>
              <div className="pr-12">
                <h3 className="text-xl font-bold mb-1 text-gray-900">See Change Impact</h3>
                <p className="text-xs text-stone-500 leading-relaxed max-w-[90%] font-medium">Understand how changes affect other events</p>
              </div>
              <div className="absolute bottom-6 right-6 w-8 h-8 rounded-full bg-white text-gray-700 border border-gray-100 flex items-center justify-center shadow-sm group-hover:scale-110 transition-transform">
                <ArrowRight className="w-4 h-4" />
              </div>
            </div>
          </Link>
        </div>

        {/* Dashboard Grid Content */}
        <div className="grid grid-cols-1 lg:grid-cols-[19fr_10fr] gap-6">
          
          {/* Left Column */}
          <div className="flex flex-col gap-6">
            
            {/* My Upcoming Events List */}
            <div className="bg-[#FAF9F8] rounded-2xl shadow-sm border border-stone-200/50 p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-gray-900">My Upcoming Events</h3>
                <button className="text-sm font-semibold text-[#7a1b32] hover:text-rose-900 flex items-center transition-colors">
                  View All <ArrowRight className="w-4 h-4 ml-1" />
                </button>
              </div>
              
              <UpcomingEvents />
            </div>
            {/* Campus Calendar */}
            <div className="bg-[#FAF9F8] rounded-2xl shadow-sm border border-stone-200/50 p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-bold text-gray-900 text-lg">Campus Calendar</h3>
                <button className="bg-[#7a1b32] hover:bg-rose-900 text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 transition-colors shadow-sm">
                  <Plus className="w-3 h-3" /> New Event
                </button>
              </div>
              
              {/* Fake Mini Calendar */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-4 px-2">
                  <button className="p-1 hover:bg-gray-100 rounded-md text-gray-600 transition-colors">&lt;</button>
                  <span className="font-bold text-sm text-gray-900">October 2026</span>
                  <button className="p-1 hover:bg-gray-100 rounded-md text-gray-600 transition-colors">&gt;</button>
                </div>
                <div className="grid grid-cols-7 text-center text-xs font-semibold text-gray-500 mb-3">
                  <div>Sun</div><div>Mon</div><div>Tue</div><div>Wed</div><div>Thu</div><div>Fri</div><div>Sat</div>
                </div>
                <div className="grid grid-cols-7 text-center text-sm gap-y-3">
                  <div className="text-gray-300">27</div><div className="text-gray-300">28</div><div className="text-gray-300">29</div><div className="text-gray-300">30</div>
                  <div className="py-1 text-gray-700">1</div><div className="py-1 text-gray-700">2</div><div className="py-1 text-gray-700">3</div>
                  
                  <div className="py-1 text-gray-700">4</div><div className="py-1 text-gray-700">5</div><div className="py-1 text-gray-700">6</div><div className="py-1 text-gray-700">7</div>
                  <div className="py-1 flex flex-col items-center font-medium text-gray-900">8 <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1"></span></div>
                  <div className="py-1 text-gray-700">9</div><div className="py-1 text-gray-700">10</div>
                  
                  <div className="py-1 text-gray-700">11</div>
                  <div className="py-1 flex flex-col items-center font-medium text-gray-900">12 <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1"></span></div>
                  <div className="py-1 text-gray-700">13</div><div className="py-1 text-gray-700">14</div><div className="py-1 text-gray-700">15</div><div className="py-1 text-gray-700">16</div><div className="py-1 text-gray-700">17</div>
                  
                  <div className="py-1 bg-[#7a1b32] text-white rounded-full mx-1 font-bold shadow-md shadow-rose-900/20">18</div>
                  <div className="py-1 text-gray-700">19</div><div className="py-1 text-gray-700">20</div>
                  <div className="py-1 flex flex-col items-center font-medium text-gray-900">21 <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1"></span></div>
                  <div className="py-1 text-gray-700">22</div><div className="py-1 text-gray-700">23</div><div className="py-1 text-gray-700">24</div>
                  
                  <div className="py-1 flex flex-col items-center text-amber-600 font-bold">25 <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1"></span></div>
                  <div className="py-1 text-gray-700">26</div><div className="py-1 text-gray-700">27</div>
                  <div className="py-1 flex flex-col items-center font-medium text-gray-900">28 <span className="w-1.5 h-1.5 rounded-full bg-rose-500 mt-1"></span></div>
                  <div className="py-1 text-gray-700">29</div>
                  <div className="py-1 flex flex-col items-center font-medium text-gray-900">30 <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1"></span></div>
                  <div className="py-1 text-gray-700">31</div>
                </div>
              </div>

              {/* Legend */}
              <div className="flex items-center justify-center gap-5 mt-6 text-xs text-gray-600 font-medium">
                <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> Confirmed</div>
                <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span> Tentative</div>
                <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-rose-400"></span> Planning</div>
              </div>
            </div>

            {/* Quick Links */}
            <div className="bg-[#FAF9F8] rounded-2xl shadow-sm border border-stone-200/50 p-6 flex-1">
              <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2 text-lg">
                <span className="w-8 h-8 rounded-full bg-rose-50 border border-rose-100 text-[#7a1b32] flex items-center justify-center">
                  <Book className="w-4 h-4" />
                </span>
                Quick Links
              </h3>
              <ul className="space-y-1">
                <li>
                  <a href="#" className="flex items-center justify-between p-3 rounded-xl hover:bg-white text-sm font-semibold text-gray-700 transition-all border border-transparent hover:border-gray-100 hover:shadow-sm">
                    <span className="flex items-center gap-3"><FileText className="w-4 h-4 text-[#7a1b32]" /> OSA Guidelines</span>
                    <ArrowRight className="w-4 h-4 text-gray-400" />
                  </a>
                </li>
                <li>
                  <a href="#" className="flex items-center justify-between p-3 rounded-xl hover:bg-white text-sm font-semibold text-gray-700 transition-all border border-transparent hover:border-gray-100 hover:shadow-sm">
                    <span className="flex items-center gap-3"><Calendar className="w-4 h-4 text-[#7a1b32]" /> Event Templates</span>
                    <ArrowRight className="w-4 h-4 text-gray-400" />
                  </a>
                </li>
                <li>
                  <a href="#" className="flex items-center justify-between p-3 rounded-xl hover:bg-white text-sm font-semibold text-gray-700 transition-all border border-transparent hover:border-gray-100 hover:shadow-sm">
                    <span className="flex items-center gap-3"><Phone className="w-4 h-4 text-[#7a1b32]" /> Contact Student Affairs</span>
                    <ArrowRight className="w-4 h-4 text-gray-400" />
                  </a>
                </li>
                <li>
                  <a href="#" className="flex items-center justify-between p-3 rounded-xl hover:bg-white text-sm font-semibold text-gray-700 transition-all border border-transparent hover:border-gray-100 hover:shadow-sm">
                    <span className="flex items-center gap-3"><HeartPulse className="w-4 h-4 text-[#7a1b32]" /> Emergency Support</span>
                    <ArrowRight className="w-4 h-4 text-gray-400" />
                  </a>
                </li>
              </ul>
            </div>
            
          </div>
        </div>

        {/* Row 2: Ask CampusCue · Promo */}
        <div className="grid grid-cols-1 lg:grid-cols-[19fr_10fr] gap-6 items-stretch mt-6">
          {/* Ask CampusCue Banner */}
          <div className="bg-[#fcf3f3] rounded-2xl p-6 border border-rose-100/50 relative overflow-hidden flex items-center shadow-sm h-48">
            <div 
              className="absolute inset-y-0 right-0 w-1/3 mix-blend-multiply opacity-20"
              style={{ 
                backgroundImage: "url('https://upload.wikimedia.org/wikipedia/commons/2/2c/Amrita_Vishwa_Vidyapeetham_coimbatore_campus.jpg')",
                backgroundSize: 'cover',
                backgroundPosition: 'left center'
              }}
            />
            <div className="absolute inset-0 bg-gradient-to-r from-[#fcf3f3] via-[#fcf3f3]/90 to-transparent z-0" />
            
            <div className="relative z-10 w-full pr-12">
              <div className="flex items-center gap-2 mb-1">
                <Sparkles className="w-6 h-6 text-[#7a1b32]" />
                <h3 className="text-2xl font-serif font-bold text-[#7a1b32]">Ask CampusCue</h3>
              </div>
              <p className="text-sm text-gray-700 mb-5 font-medium">Get answers from Amrita&apos;s official guidelines, venue details, and past events.</p>
              
              <div className="relative max-w-3xl">
                <input type="text" placeholder="Ask anything... (e.g. Can we host a food stall? / When is the next free slot at CKB?)" className="w-full bg-white rounded-full pl-6 pr-14 py-3.5 text-sm focus:outline-none focus:ring-2 focus:ring-rose-200 shadow-sm border border-rose-50 placeholder-gray-400 font-medium" />
                <button className="absolute right-1.5 top-1.5 bottom-1.5 w-11 bg-[#7a1b32] rounded-full flex items-center justify-center text-white hover:bg-rose-900 transition-colors shadow-md">
                  <Send className="w-4 h-4 ml-0.5" />
                </button>
              </div>
              
              <div className="flex gap-2 mt-4 overflow-x-auto pb-1 scrollbar-hide">
                <span className="whitespace-nowrap px-4 py-1.5 bg-rose-900/5 text-rose-900 rounded-full text-xs font-semibold cursor-pointer hover:bg-rose-900/10 transition-colors border border-rose-900/10 shadow-sm">Can we host a food stall?</span>
                <span className="whitespace-nowrap px-4 py-1.5 bg-rose-900/5 text-rose-900 rounded-full text-xs font-semibold cursor-pointer hover:bg-rose-900/10 transition-colors border border-rose-900/10 shadow-sm">Steps to book a venue</span>
                <span className="whitespace-nowrap px-4 py-1.5 bg-rose-900/5 text-rose-900 rounded-full text-xs font-semibold cursor-pointer hover:bg-rose-900/10 transition-colors border border-rose-900/10 shadow-sm">What is the refund policy?</span>
                <span className="whitespace-nowrap px-4 py-1.5 bg-rose-900/5 text-rose-900 rounded-full text-xs font-semibold cursor-pointer hover:bg-rose-900/10 transition-colors border border-rose-900/10 shadow-sm">Who to contact for technical support?</span>
              </div>
            </div>
          </div>

          {/* Promo block */}
          <div className="bg-[#FAF8F5] rounded-2xl p-6 relative overflow-hidden h-48 flex items-center shadow-lg border border-transparent">
             <div className="absolute inset-0 z-0 bg-cover bg-center" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1541339907198-e08756dedf3f?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80')" }}></div>
             <div className="absolute inset-0 bg-gradient-to-t from-white/90 via-white/70 to-transparent z-0" />
             <div className="absolute inset-0 bg-gradient-to-l from-white/95 via-white/80 to-transparent z-0" />
             <div className="relative z-10 flex-1 flex flex-col justify-center items-end pr-4 mt-8">
               <p className="text-gray-900 font-serif text-lg leading-snug text-right max-w-[140px] drop-shadow-sm font-medium">
                 Events build the campus we remember.
               </p>
               <div className="w-12 h-0.5 bg-[#7a1b32] mt-3 rounded"></div>
             </div>
          </div>
        </div>

      </div>
    </div>
  );
}
