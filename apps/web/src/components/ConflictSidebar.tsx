import React from 'react';

const ConflictSidebar = () => {
  return (
    <div className="w-80 bg-white border-l border-gray-200 p-5 flex flex-col h-full overflow-y-auto">
      <div className="mb-6">
        <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
          <span className="text-red-500">⚠️</span> Potential Clash
        </h2>
        <p className="text-sm text-gray-500 mt-1">
          Multiple interests for the same venue.
        </p>
      </div>

      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <div className="flex items-start gap-3">
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-red-800">Venue Overlap</h3>
            <p className="text-xs text-red-600 mt-1">
              Both events are requesting Acharya Hall at overlapping times on Day 5.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-4 flex-1">
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">Event 1</span>
          </div>
          <h4 className="font-medium text-gray-800">INIT AI Hackathon</h4>
          <p className="text-xs text-gray-500 mt-1">Time: 10:00 AM - 4:00 PM</p>
          <p className="text-xs text-gray-500">Organizer: AI Club</p>
          <div className="mt-3 flex gap-2">
            <button className="flex-1 bg-white border border-gray-300 text-gray-700 text-xs font-medium py-1.5 rounded hover:bg-gray-50">
              Contact Organizer
            </button>
          </div>
        </div>

        <div className="flex items-center justify-center">
          <span className="text-gray-400 text-xs font-bold bg-white px-2 py-1 border border-gray-200 rounded-full">VS</span>
        </div>

        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-semibold text-teal-600 bg-teal-50 px-2 py-0.5 rounded">Event 2</span>
          </div>
          <h4 className="font-medium text-gray-800">IDEA Workshop</h4>
          <p className="text-xs text-gray-500 mt-1">Time: 2:00 PM - 5:00 PM</p>
          <p className="text-xs text-gray-500">Organizer: Innovation Cell</p>
          <div className="mt-3 flex gap-2 flex-col">
            <button className="w-full bg-white border border-gray-300 text-gray-700 text-xs font-medium py-1.5 rounded hover:bg-gray-50">
              Contact Organizer
            </button>
            <button className="w-full bg-indigo-600 text-white text-xs font-medium py-1.5 rounded hover:bg-indigo-700">
              Try Alternate Slot
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConflictSidebar;
