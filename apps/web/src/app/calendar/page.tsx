import React from 'react';
import CalendarGrid from '@/components/CalendarGrid';
import ConflictSidebar from '@/components/ConflictSidebar';

export default function CalendarPage() {
  return (
    <div className="flex h-[calc(100vh-64px)] bg-[#F5EEE9] overflow-hidden">
      {/* Main Calendar Area */}
      <CalendarGrid />
      
      {/* Conflict Sidebar */}
      <ConflictSidebar />
    </div>
  );
}
