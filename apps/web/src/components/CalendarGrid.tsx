'use client';
import React, { useState } from 'react';

const CalendarGrid = () => {
  const [activeTab, setActiveTab] = useState('Month');
  const events = [
    { title: 'Tech Talk', day: 1, type: 'approved' },
    { title: 'Cultural Fest', day: 2, type: 'approved' },
    { title: 'INIT AI Hackathon (Tentative)', day: 4, type: 'tentative', conflict: true },
    { title: 'IDEA Workshop (Tentative)', day: 4, type: 'tentative', conflict: true },
    { title: 'Robotics Workshop (Approved)', day: 5, type: 'approved' },
  ];

  return (
    <div className="flex-1 p-8 lg:p-12 overflow-y-auto">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-end mb-8">
          <div>
            <h1 className="text-3xl font-serif font-bold text-[#7a1b32] mb-1">Campus Calendar</h1>
            <p className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Plan and visualize events</p>
          </div>
          
          <div className="flex space-x-1 bg-white rounded-full p-1 shadow-sm border border-rose-50">
            {['Month', 'Week', 'List'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-5 py-2 text-xs font-bold uppercase tracking-wider rounded-full transition-all ${
                  activeTab === tab
                    ? 'bg-[#7a1b32] text-white shadow-md'
                    : 'text-gray-500 hover:text-gray-900 hover:bg-stone-50'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border-none overflow-hidden">
          <div className="grid grid-cols-7 border-b border-stone-100 bg-[#FFF5F0]/50">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
              <div key={day} className="py-4 text-center text-xs font-bold uppercase tracking-wider text-[#7a1b32] border-r last:border-r-0 border-stone-100/50">
                {day}
              </div>
            ))}
          </div>
          
          <div className="grid grid-cols-7 auto-rows-[minmax(140px,auto)]">
            {Array.from({ length: 35 }).map((_, index) => {
              const dayEvents = events.filter(e => e.day === index);
              const isToday = index === 18; // Mock today
              return (
                <div key={index} className={`border-r border-b border-stone-100/50 p-2.5 relative min-h-[140px] last:border-r-0 transition-colors hover:bg-stone-50/30 ${isToday ? 'bg-rose-50/30' : ''}`}>
                  <span className={`flex items-center justify-center w-7 h-7 text-xs font-bold rounded-full mb-1 ${isToday ? 'bg-[#7a1b32] text-white shadow-md' : 'text-gray-400'}`}>
                    {index + 1}
                  </span>
                  
                  <div className="mt-2 space-y-1.5">
                    {dayEvents.map((event, i) => (
                      <div 
                        key={i} 
                        className={`text-[10px] p-2 rounded-lg font-bold uppercase tracking-wide leading-tight shadow-sm border ${
                          event.conflict ? 'bg-rose-50 border-rose-100 text-rose-800' :
                          event.type === 'tentative' ? 'bg-amber-50 border-amber-100 text-amber-700' :
                          'bg-emerald-50 border-emerald-100 text-emerald-700'
                        }`}
                      >
                        {event.title}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CalendarGrid;
