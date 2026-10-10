import React from 'react';
import CalendarGrid from '@/components/CalendarGrid';
import ConflictSidebar from '@/components/ConflictSidebar';

export default function CalendarPage() {
  return (
    <div className="flex h-screen bg-white">
      {/* Main Calendar Area */}
      <CalendarGrid />
      
      {/* Conflict Sidebar */}
      <ConflictSidebar />
    </div>
  );
}
