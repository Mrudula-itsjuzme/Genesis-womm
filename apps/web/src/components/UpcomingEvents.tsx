"use client";
import React, { useEffect, useState } from "react";
import { MapPin, Clock, ArrowRight } from "lucide-react";
import { EventOut, EventStatus } from "@/types/events";
import { demoLogin, getMyEvents } from "@/lib/api";

const statusStyles: Record<EventStatus, string> = {
  CONFIRMED: "bg-emerald-100 text-emerald-700",
  TENTATIVE: "bg-amber-100 text-amber-700",
  DRAFT: "bg-gray-100 text-gray-700",
  SUBMITTED: "bg-blue-100 text-blue-700",
  ACKNOWLEDGED: "bg-indigo-100 text-indigo-700",
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
    status: "DRAFT",
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

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-20 bg-stone-100 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {events.map((evt) => (
        <div
          key={evt.id}
          className="flex items-center justify-between p-4 bg-white border border-stone-100 shadow-sm rounded-xl hover:shadow-md transition-shadow group"
        >
          <div className="flex items-center gap-4">
            <div className="flex flex-col items-center justify-center bg-rose-50 text-rose-900 rounded-xl w-14 h-14 border border-rose-100/50">
              <span className="text-[10px] font-bold uppercase tracking-wider">
                {formatMonth(evt.start_at)}
              </span>
              <span className="text-xl font-bold leading-none">
                {formatDay(evt.start_at)}
              </span>
            </div>
            <div>
              <h4 className="font-bold text-gray-900 text-[15px]">
                {evt.title}
              </h4>
              <p className="text-xs text-gray-500 flex items-center mt-1">
                <MapPin className="w-3 h-3 mr-1" />{" "}
                {evt.resource_id || "Venue TBD"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-8">
            <p className="text-sm font-medium text-gray-600 flex items-center">
              <Clock className="w-4 h-4 mr-2 text-gray-400" />{" "}
              {formatTime(evt.start_at)}
            </p>
            <div className="w-24 text-right">
              <span
                className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${statusStyles[evt.status] || statusStyles.DRAFT}`}
              >
                {evt.status.charAt(0) + evt.status.slice(1).toLowerCase()}
              </span>
            </div>
            <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-rose-900 transition-colors" />
          </div>
        </div>
      ))}
    </div>
  );
}
