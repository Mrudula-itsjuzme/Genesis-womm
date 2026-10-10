import React from 'react';

const CalendarGrid = () => {
  const events = [
    { title: 'Tech Talk', day: 1, type: 'approved' },
    { title: 'Cultural Fest', day: 2, type: 'approved' },
    { title: 'INIT AI Hackathon (Tentative)', day: 4, type: 'tentative', conflict: true },
    { title: 'IDEA Workshop (Tentative)', day: 4, type: 'tentative', conflict: true },
    { title: 'Robotics Workshop (Approved)', day: 5, type: 'approved' },
  ];

  return (
    <div className="flex-1 p-4 bg-gray-50 overflow-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Tentative Calendar</h1>
        <div className="flex space-x-2 bg-white rounded-lg p-1 border border-gray-200">
          <button className="px-4 py-1.5 text-sm font-medium bg-gray-100 text-gray-800 rounded-md">Month</button>
          <button className="px-4 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 rounded-md">Week</button>
          <button className="px-4 py-1.5 text-sm font-medium text-gray-600 hover:bg-gray-50 rounded-md">List</button>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl shadow-sm">
        <div className="grid grid-cols-7 border-b border-gray-200 bg-gray-50 rounded-t-xl">
          {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
            <div key={day} className="py-3 text-center text-sm font-semibold text-gray-600 border-r last:border-r-0 border-gray-200">
              {day}
            </div>
          ))}
        </div>
        
        <div className="grid grid-cols-7 auto-rows-[minmax(120px,auto)]">
          {Array.from({ length: 35 }).map((_, index) => {
            const dayEvents = events.filter(e => e.day === index);
            return (
              <div key={index} className="border-r border-b border-gray-100 p-2 relative min-h-[120px] last:border-r-0">
                <span className="text-sm text-gray-400 font-medium">{index + 1}</span>
                <div className="mt-1 space-y-1">
                  {dayEvents.map((event, i) => (
                    <div 
                      key={i} 
                      className={`text-xs p-1.5 rounded truncate border ${
                        event.conflict ? 'bg-red-50 border-red-200 text-red-700' :
                        event.type === 'tentative' ? 'bg-yellow-50 border-yellow-200 text-yellow-700' :
                        'bg-blue-50 border-blue-200 text-blue-700'
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
  );
};

export default CalendarGrid;
