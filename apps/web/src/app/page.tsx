import React from 'react';
import Link from 'next/link';
import { Calendar, Search, MapPin, FileText, BarChart2, Plus, ArrowRight, Phone, HeartPulse, Send, Book, Building, CheckCircle2, HelpCircle, Clock } from 'lucide-react';

export default function Dashboard() {
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative w-full h-[400px] overflow-hidden flex flex-col justify-center px-8 md:px-16 lg:px-24">
        {/* Background Image Placeholder */}
        <div 
          className="absolute inset-0 z-0 bg-cover bg-center"
          style={{ 
            backgroundImage: "url('https://upload.wikimedia.org/wikipedia/commons/2/2c/Amrita_Vishwa_Vidyapeetham_coimbatore_campus.jpg')",
            filter: "brightness(0.65) saturate(1.1)"
          }}
        />
        
        <div className="relative z-10 text-white mt-12 max-w-4xl">
          <h2 className="text-xl md:text-2xl font-light mb-1 drop-shadow-md">Good evening,</h2>
          <h1 className="text-5xl md:text-7xl font-serif mb-4 drop-shadow-md">Mrudula</h1>
          <p className="text-lg md:text-xl font-light mb-8 opacity-90 drop-shadow-md">Let's make something happen on campus.</p>
          
          {/* Main Search Bar */}
          <div className="relative max-w-2xl bg-white/95 backdrop-blur-sm rounded-full shadow-lg flex items-center px-4 py-3 border border-white/20 transition-all hover:bg-white focus-within:bg-white focus-within:ring-2 focus-within:ring-rose-500">
            <Search className="w-5 h-5 text-gray-500 mr-3" />
            <input 
              type="text" 
              placeholder="Search for venues, events, policies, or ask anything..." 
              className="flex-1 bg-transparent border-none focus:ring-0 text-gray-800 placeholder-gray-500 text-sm md:text-base outline-none"
            />
            <div className="hidden sm:flex items-center space-x-1 text-xs text-gray-400 font-mono px-2">
              <kbd className="px-2 py-1 rounded bg-gray-100 border border-gray-200">Ctrl</kbd>
              <kbd className="px-2 py-1 rounded bg-gray-100 border border-gray-200">K</kbd>
            </div>
          </div>
        </div>

        {/* Right side floating text */}
        <div className="absolute right-12 top-1/2 -translate-y-1/2 hidden lg:block z-10 text-right">
          <p className="text-white text-lg font-light tracking-wide leading-relaxed drop-shadow-md opacity-90">
            Same<br/>campus.<br/>New<br/>possibilities.
          </p>
        </div>
      </section>

      {/* Main Content Area */}
      <div className="max-w-[1400px] mx-auto px-6 lg:px-12 -mt-16 relative z-20 pb-20">
        
        {/* Action Cards Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
          
          {/* Card 1 */}
          <Link href="/plan" className="bg-gradient-to-br from-rose-900 to-rose-950 rounded-2xl p-6 text-white shadow-xl hover:shadow-2xl hover:-translate-y-1 transition-all flex flex-col justify-between group h-44">
            <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center mb-4 backdrop-blur-md">
              <Calendar className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold mb-1 group-hover:translate-x-1 transition-transform">Plan an Event</h3>
              <div className="flex items-center justify-between">
                <p className="text-xs text-rose-100/70 max-w-[80%]">Find a date, check availability and get started</p>
                <div className="w-8 h-8 rounded-full bg-white text-rose-900 flex items-center justify-center shadow-md">
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            </div>
          </Link>

          {/* Card 2 */}
          <Link href="/venues" className="bg-white border border-gray-200 rounded-2xl p-6 text-gray-800 shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all flex flex-col justify-between group h-44 relative overflow-hidden">
            <div 
              className="absolute inset-0 z-0 bg-cover bg-center opacity-40 transition-transform group-hover:scale-105 duration-700"
              style={{ backgroundImage: "url('https://images.unsplash.com/photo-1590457635677-7871b6d05f3b?auto=format&fit=crop&w=600&q=80')" }}
            />
            <div className="absolute inset-0 bg-gradient-to-r from-white/95 via-white/80 to-transparent z-0" />
            <div className="relative z-10">
              <div className="w-10 h-10 rounded-xl bg-white shadow-sm text-rose-800 flex items-center justify-center mb-4">
                <MapPin className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold mb-1 text-gray-900 group-hover:translate-x-1 transition-transform">Explore Venues</h3>
                <div className="flex items-center justify-between">
                  <p className="text-xs text-gray-600 max-w-[80%] font-medium">View halls, classrooms, labs and open spaces</p>
                  <div className="w-8 h-8 rounded-full bg-white border border-gray-200 text-gray-600 flex items-center justify-center shadow-sm">
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </div>
              </div>
            </div>
          </Link>

          {/* Card 3 */}
          <Link href="/policy" className="bg-white border border-gray-200 rounded-2xl p-6 text-gray-800 shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all flex flex-col justify-between group h-44 relative overflow-hidden">
            <div 
              className="absolute inset-0 z-0 bg-cover bg-center opacity-40 transition-transform group-hover:scale-105 duration-700"
              style={{ backgroundImage: "url('https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?auto=format&fit=crop&w=600&q=80')" }}
            />
            <div className="absolute inset-0 bg-gradient-to-r from-white/95 via-white/80 to-transparent z-0" />
            <div className="relative z-10">
              <div className="w-10 h-10 rounded-xl bg-white shadow-sm text-rose-800 flex items-center justify-center mb-4">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold mb-1 text-gray-900 group-hover:translate-x-1 transition-transform">Ask a Policy Question</h3>
                <div className="flex items-center justify-between">
                  <p className="text-xs text-gray-600 max-w-[80%] font-medium">Get instant answers from OSA guidelines</p>
                  <div className="w-8 h-8 rounded-full bg-white border border-gray-200 text-gray-600 flex items-center justify-center shadow-sm">
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </div>
              </div>
            </div>
          </Link>

          {/* Card 4 */}
          <Link href="/changes" className="bg-white border border-gray-200 rounded-2xl p-6 text-gray-800 shadow-lg hover:shadow-xl hover:-translate-y-1 transition-all flex flex-col justify-between group h-44 relative overflow-hidden">
             <div 
              className="absolute inset-0 z-0 bg-cover bg-center opacity-40 transition-transform group-hover:scale-105 duration-700"
              style={{ backgroundImage: "url('https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=600&q=80')" }}
            />
            <div className="absolute inset-0 bg-gradient-to-r from-white/95 via-white/80 to-transparent z-0" />
            <div className="relative z-10">
              <div className="w-10 h-10 rounded-xl bg-white shadow-sm text-amber-600 flex items-center justify-center mb-4">
                <BarChart2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold mb-1 text-gray-900 group-hover:translate-x-1 transition-transform">See Change Impact</h3>
                <div className="flex items-center justify-between">
                  <p className="text-xs text-gray-600 max-w-[80%] font-medium">Understand how changes affect other events</p>
                  <div className="w-8 h-8 rounded-full bg-white border border-gray-200 text-gray-600 flex items-center justify-center shadow-sm">
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </div>
              </div>
            </div>
          </Link>

        </div>

        {/* Dashboard Grid Row */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Left Column: Upcoming Events & Ask CampusCue */}
          <div className="lg:col-span-8 space-y-6">
            
            {/* My Upcoming Events */}
            <div>
              <div className="flex items-center justify-between mb-4 px-1">
                <h3 className="text-xl font-bold text-gray-900">My Upcoming Events</h3>
                <button className="text-sm font-semibold text-rose-800 hover:text-rose-900 flex items-center gap-1">
                  View All <ArrowRight className="w-4 h-4" />
                </button>
              </div>
              
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-2">
                
                {/* Event Item 1 */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 hover:bg-gray-50 rounded-xl transition-colors cursor-pointer border-b border-gray-50 last:border-0">
                  <div className="flex items-center gap-6">
                    <div className="flex flex-col items-center justify-center w-14 h-14 rounded-xl bg-rose-50 text-rose-900">
                      <span className="text-[10px] font-bold uppercase tracking-wider">Oct</span>
                      <span className="text-xl font-black">18</span>
                    </div>
                    <div>
                      <h4 className="font-bold text-gray-900">WOMM Orientation</h4>
                      <div className="flex items-center text-xs text-gray-500 mt-1 gap-1">
                        <MapPin className="w-3.5 h-3.5" /> Amphitheatre
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6 mt-4 sm:mt-0">
                    <div className="flex items-center text-sm text-gray-500 gap-1.5">
                      <Clock className="w-4 h-4" /> 10:00 AM – 1:00 PM
                    </div>
                    <div className="w-24 text-right">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                        Confirmed
                      </span>
                    </div>
                    <ArrowRight className="w-4 h-4 text-gray-300" />
                  </div>
                </div>

                {/* Event Item 2 */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 hover:bg-gray-50 rounded-xl transition-colors cursor-pointer border-b border-gray-50 last:border-0">
                  <div className="flex items-center gap-6">
                    <div className="flex flex-col items-center justify-center w-14 h-14 rounded-xl bg-rose-50 text-rose-900">
                      <span className="text-[10px] font-bold uppercase tracking-wider">Oct</span>
                      <span className="text-xl font-black">25</span>
                    </div>
                    <div>
                      <h4 className="font-bold text-gray-900">Design Workshop</h4>
                      <div className="flex items-center text-xs text-gray-500 mt-1 gap-1">
                        <MapPin className="w-3.5 h-3.5" /> ICTS Lab 2
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6 mt-4 sm:mt-0">
                    <div className="flex items-center text-sm text-gray-500 gap-1.5">
                      <Clock className="w-4 h-4" /> 2:00 PM – 5:00 PM
                    </div>
                    <div className="w-24 text-right">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
                        Tentative
                      </span>
                    </div>
                    <ArrowRight className="w-4 h-4 text-gray-300" />
                  </div>
                </div>

                {/* Event Item 3 */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 hover:bg-gray-50 rounded-xl transition-colors cursor-pointer border-b border-gray-50 last:border-0">
                  <div className="flex items-center gap-6">
                    <div className="flex flex-col items-center justify-center w-14 h-14 rounded-xl bg-rose-50 text-rose-900">
                      <span className="text-[10px] font-bold uppercase tracking-wider">Nov</span>
                      <span className="text-xl font-black">02</span>
                    </div>
                    <div>
                      <h4 className="font-bold text-gray-900">Speaker Session</h4>
                      <div className="flex items-center text-xs text-gray-500 mt-1 gap-1">
                        <MapPin className="w-3.5 h-3.5" /> Mini Auditorium
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-6 mt-4 sm:mt-0">
                    <div className="flex items-center text-sm text-gray-500 gap-1.5">
                      <Clock className="w-4 h-4" /> 11:00 AM – 1:00 PM
                    </div>
                    <div className="w-24 text-right">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-pink-100 text-pink-800">
                        Planning
                      </span>
                    </div>
                    <ArrowRight className="w-4 h-4 text-gray-300" />
                  </div>
                </div>

              </div>
            </div>

            {/* Ask CampusCue Bottom Banner */}
            <div className="bg-gradient-to-r from-rose-50 to-orange-50 rounded-2xl p-6 border border-rose-100/50 shadow-sm relative overflow-hidden">
               <div className="flex items-start gap-4 relative z-10">
                <div className="p-3 bg-white rounded-xl shadow-sm text-rose-800">
                  <HelpCircle className="w-6 h-6" />
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-bold text-gray-900 mb-1">Ask CampusCue</h3>
                  <p className="text-sm text-gray-600 mb-4">Get answers from Amrita's official guidelines, venue details, and past events.</p>
                  
                  <div className="relative mb-4">
                    <input 
                      type="text" 
                      placeholder="Ask anything... (e.g. Can we host a food stall? / When is the next free slot at CKB?)"
                      className="w-full pl-4 pr-12 py-3 rounded-xl border border-gray-200 shadow-inner focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-transparent"
                    />
                    <button className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-rose-900 text-white rounded-lg hover:bg-rose-800 transition-colors">
                      <Send className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button className="px-3 py-1.5 rounded-full bg-rose-900/5 text-rose-900 text-xs font-medium hover:bg-rose-900/10 transition-colors">Can we host a food stall?</button>
                    <button className="px-3 py-1.5 rounded-full bg-rose-900/5 text-rose-900 text-xs font-medium hover:bg-rose-900/10 transition-colors">Steps to book a venue</button>
                    <button className="px-3 py-1.5 rounded-full bg-rose-900/5 text-rose-900 text-xs font-medium hover:bg-rose-900/10 transition-colors">What is the refund policy?</button>
                    <button className="px-3 py-1.5 rounded-full bg-rose-900/5 text-rose-900 text-xs font-medium hover:bg-rose-900/10 transition-colors">Who to contact for technical support?</button>
                  </div>
                </div>
               </div>
            </div>

          </div>
          
          {/* Right Column: Calendar & Quick Links */}
          <div className="lg:col-span-4 space-y-6">
            
            {/* Campus Calendar */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-bold text-gray-900">Campus Calendar</h3>
                <button className="bg-rose-900 hover:bg-rose-800 text-white text-xs font-semibold px-3 py-1.5 rounded-md flex items-center gap-1 transition-colors">
                  <Plus className="w-3 h-3" /> New Event
                </button>
              </div>
              
              {/* Fake Mini Calendar */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-4">
                  <button className="p-1 hover:bg-gray-100 rounded text-gray-600">&lt;</button>
                  <span className="font-semibold text-sm">October 2026</span>
                  <button className="p-1 hover:bg-gray-100 rounded text-gray-600">&gt;</button>
                </div>
                <div className="grid grid-cols-7 text-center text-xs font-medium text-gray-400 mb-2">
                  <div>Sun</div><div>Mon</div><div>Tue</div><div>Wed</div><div>Thu</div><div>Fri</div><div>Sat</div>
                </div>
                <div className="grid grid-cols-7 text-center text-sm gap-y-2">
                  <div className="text-gray-300">27</div><div className="text-gray-300">28</div><div className="text-gray-300">29</div><div className="text-gray-300">30</div>
                  <div className="py-1">1</div><div className="py-1">2</div><div className="py-1">3</div>
                  
                  <div className="py-1">4</div><div className="py-1">5</div><div className="py-1">6</div><div className="py-1">7</div>
                  <div className="py-1 flex flex-col items-center">8 <span className="w-1 h-1 rounded-full bg-amber-400 mt-0.5"></span></div>
                  <div className="py-1">9</div><div className="py-1">10</div>
                  
                  <div className="py-1">11</div>
                  <div className="py-1 flex flex-col items-center">12 <span className="w-1 h-1 rounded-full bg-emerald-500 mt-0.5"></span></div>
                  <div className="py-1">13</div><div className="py-1">14</div><div className="py-1">15</div><div className="py-1">16</div><div className="py-1">17</div>
                  
                  <div className="py-1 bg-rose-900 text-white rounded-full mx-1">18</div>
                  <div className="py-1">19</div><div className="py-1">20</div>
                  <div className="py-1 flex flex-col items-center">21 <span className="w-1 h-1 rounded-full bg-emerald-500 mt-0.5"></span></div>
                  <div className="py-1">22</div><div className="py-1">23</div><div className="py-1">24</div>
                  
                  <div className="py-1 flex flex-col items-center text-amber-600 font-bold">25 <span className="w-1 h-1 rounded-full bg-amber-400 mt-0.5"></span></div>
                  <div className="py-1">26</div><div className="py-1">27</div>
                  <div className="py-1 flex flex-col items-center">28 <span className="w-1 h-1 rounded-full bg-pink-500 mt-0.5"></span></div>
                  <div className="py-1">29</div>
                  <div className="py-1 flex flex-col items-center">30 <span className="w-1 h-1 rounded-full bg-emerald-500 mt-0.5"></span></div>
                  <div className="py-1">31</div>
                </div>
              </div>

              {/* Legend */}
              <div className="flex items-center justify-center gap-4 mt-6 text-xs text-gray-500">
                <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-500"></span> Confirmed</div>
                <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-400"></span> Tentative</div>
                <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-pink-400"></span> Planning</div>
              </div>
            </div>

            {/* Quick Links */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
              <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                <span className="w-8 h-8 rounded-full bg-rose-50 text-rose-900 flex items-center justify-center">
                  <Book className="w-4 h-4" />
                </span>
                Quick Links
              </h3>
              <ul className="space-y-1">
                <li>
                  <a href="#" className="flex items-center justify-between p-3 rounded-xl hover:bg-gray-50 text-sm font-medium text-gray-700 transition-colors border border-transparent hover:border-gray-100">
                    <span className="flex items-center gap-3"><FileText className="w-4 h-4 text-gray-400" /> OSA Guidelines</span>
                    <ArrowRight className="w-4 h-4 text-gray-300" />
                  </a>
                </li>
                <li>
                  <a href="#" className="flex items-center justify-between p-3 rounded-xl hover:bg-gray-50 text-sm font-medium text-gray-700 transition-colors border border-transparent hover:border-gray-100">
                    <span className="flex items-center gap-3"><Calendar className="w-4 h-4 text-gray-400" /> Event Templates</span>
                    <ArrowRight className="w-4 h-4 text-gray-300" />
                  </a>
                </li>
                <li>
                  <a href="#" className="flex items-center justify-between p-3 rounded-xl hover:bg-gray-50 text-sm font-medium text-gray-700 transition-colors border border-transparent hover:border-gray-100">
                    <span className="flex items-center gap-3"><Phone className="w-4 h-4 text-gray-400" /> Contact Student Affairs</span>
                    <ArrowRight className="w-4 h-4 text-gray-300" />
                  </a>
                </li>
                <li>
                  <a href="#" className="flex items-center justify-between p-3 rounded-xl hover:bg-gray-50 text-sm font-medium text-gray-700 transition-colors border border-transparent hover:border-gray-100">
                    <span className="flex items-center gap-3"><HeartPulse className="w-4 h-4 text-rose-500" /> Emergency Support</span>
                    <ArrowRight className="w-4 h-4 text-gray-300" />
                  </a>
                </li>
              </ul>
            </div>
            
            {/* Promo block */}
            <div className="bg-[#FAF8F5] rounded-2xl p-6 border border-[#F2EDE4] relative overflow-hidden h-36 flex items-center shadow-inner">
               <div className="absolute inset-0 z-0 bg-cover bg-center opacity-30" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1541339907198-e08756dedf3f?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80')" }}></div>
               <div className="relative z-10 flex-1 flex flex-col justify-center items-end pr-4">
                 <p className="text-gray-800 font-serif text-lg leading-snug text-right max-w-[120px]">
                   Events build the campus we remember.
                 </p>
                 <div className="w-8 h-0.5 bg-rose-800 mt-3 rounded"></div>
               </div>
            </div>

          </div>

        </div>
      </div>
    </div>
  );
}
