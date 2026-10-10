"use client";
import React, { useEffect, useState } from "react";
import { MapPin, Clock, ArrowRight } from "lucide-react";
import { EventOut, EventStatus } from "@/types/events";
import { demoLogin, getMyEvents } from "@/lib/api";

const statusStyles: Record<EventStatus, string> = {
  CONFIRMED: "bg-emerald-50 text-emerald-700",
  TENTATIVE: "bg-amber-50 text-amber-700",
  DRAFT: "bg-rose-50 text-rose-700",
  SUBMITTED: "bg-blue-50 text-blue-700",
  ACKNOWLEDGED: "bg-indigo-50 text-indigo-700",
};

// Fallback mock data in case backend is offline
const MOCK_EVENTS: EventOut[] = [
  {
    id: "1",
    club_id: "1",
    title: "WOMM Orientation",
    description: "",
    start_at: "2026-10-18T10:00:00Z",
    end_at: "2026-10-18T13:00:00Z",
    audience_tags: [],
    status: "CONFIRMED",
    revision: 1,
    venue_availability: "UNKNOWN",
    synthetic: true,
    created_at: "",
    updated_at: "",
    resource_id: "Amphitheatre",
  },
  {
    id: "2",
    club_id: "1",
    title: "Design Workshop",
    description: "",
    start_at: "2026-10-25T14:00:00Z",
    end_at: "2026-10-25T17:00:00Z",
    audience_tags: [],
    status: "TENTATIVE",
    revision: 1,
    venue_availability: "UNKNOWN",
    synthetic: true,
    created_at: "",
    updated_at: "",
    resource_id: "ICTS Lab 2",
  },
  {
    id: "3",
    club_id: "1",
    title: "Speaker Session",
    description: "",
    start_at: "2026-11-02T11:00:00Z",
    end_at: "2026-11-02T13:00:00Z",
    audience_tags: [],
    status: "DRAFT", // Rendered as Planning
    revision: 1,
    venue_availability: "UNKNOWN",
    synthetic: true,
    created_at: "",
    updated_at: "",
    resource_id: "Mini Auditorium",
  },
];

export default function UpcomingEvents() {
  const [events, setEvents] = useState<EventOut[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        // Automatically attempt demo login
        const session = await demoLogin("mrudula@am.students.amrita.edu");
        const data = await getMyEvents(session.access_token);
        setEvents(data.length > 0 ? data : MOCK_EVENTS);
      } catch (err) {
        // Fallback to mock data if backend is offline
        console.warn("Backend unavailable, using mock events", err);
        setEvents(MOCK_EVENTS);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const formatMonth = (iso: string) => {
    const d = new Date(iso);
    return isNaN(d.getTime())
      ? "OCT"
      : d.toLocaleDateString("en-US", { month: "short" });
  };
  const formatDay = (iso: string) => {
    const d = new Date(iso);
    return isNaN(d.getTime())
      ? "18"
      : d.toLocaleDateString("en-US", { day: "2-digit" });
  };
  const formatTime = (iso: string) => {
    const d = new Date(iso);
    return isNaN(d.getTime())
      ? "10:00 AM"
      : d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  };

  const formatEndTime = (iso: string) => {
    const d = new Date(iso);
    return isNaN(d.getTime())
      ? "1:00 PM"
      : d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  };

  if (loading) {
    return (
      <div className="flex flex-col animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 bg-stone-50 rounded-xl mb-4" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      {events.map((evt, idx) => (
        <div
          key={evt.id}
          className={`flex min-w-0 flex-col gap-3 py-4 transition-colors hover:bg-stone-50/50 sm:flex-row sm:items-center sm:justify-between sm:gap-0 ${idx !== events.length - 1 ? 'border-b border-stone-100 border-dashed' : ''}`}
        >
          <div className="flex min-w-0 items-center gap-3 sm:w-[40%] sm:gap-6">
            <div className="flex w-10 shrink-0 flex-col items-center justify-center">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#7a1b32]">
                {formatMonth(evt.start_at)}
              </span>
              <span className="text-xl font-bold leading-none text-gray-900 mt-0.5">
                {formatDay(evt.start_at)}
              </span>
            </div>
            <div className="min-w-0">
              <h4 className="break-words font-bold text-gray-900 text-sm tracking-tight">
                {evt.title}
              </h4>
              <p className="text-[11px] text-gray-500 font-semibold flex items-center mt-1 uppercase tracking-wider">
                <MapPin className="w-3 h-3 mr-1 text-gray-400" />{" "}
                {evt.resource_id || "Venue TBD"}
              </p>
            </div>
          </div>

          <div className="flex min-w-0 flex-wrap items-center justify-between gap-2 sm:flex-1 sm:flex-nowrap sm:gap-4">
            <p className="flex min-w-0 items-center text-[11px] font-semibold uppercase tracking-wider text-gray-500 sm:w-36">
              <Clock className="w-3.5 h-3.5 mr-1.5 text-gray-400" />{" "}
              {formatTime(evt.start_at)} - {formatEndTime(evt.end_at || evt.start_at)}
            </p>

            <div className="flex shrink-0 justify-end sm:w-24">
              <span
                className={`inline-flex items-center justify-center px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${statusStyles[evt.status] || statusStyles.DRAFT}`}
              >
                {evt.status === 'DRAFT' ? 'PLANNING' : evt.status}
              </span>
            </div>

            <div className="hidden w-6 shrink-0 justify-end sm:flex">
              <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-gray-600 transition-colors" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
