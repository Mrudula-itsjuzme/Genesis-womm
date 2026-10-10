'use client';

import { useMemo, useState } from 'react';
import { AlertTriangle, ArrowRight, CalendarDays, RotateCcw, ShieldAlert } from 'lucide-react';
import { CAMPUS_CALENDAR_EVENTS, getHolidayForDate, type CampusCalendarEvent } from '@/lib/campus-calendar-data';

const editableEvents = CAMPUS_CALENDAR_EVENTS.filter((event) => event.synthetic);
const minuteOfDay = (time: string) => {
    const [hour, minute] = time.split(':').map(Number);
    return hour * 60 + minute;
};
const timeLabel = (time: string) => {
    const [hourText, minute] = time.split(':');
    const hour = Number(hourText);
    return `${hour % 12 || 12}:${minute} ${hour < 12 ? 'AM' : 'PM'}`;
};
const statusLabel = (event: CampusCalendarEvent) => `${event.status[0]}${event.status.slice(1).toLowerCase()}${event.synthetic ? ' · demo' : ''}`;

export default function ChangeImpactList({ initialEventId }: { initialEventId?: string }) {
    const initialEvent = editableEvents.find((event) => event.id === initialEventId) ?? editableEvents[0];
    const [selectedId, setSelectedId] = useState(initialEvent?.id ?? '');
    const [proposedDate, setProposedDate] = useState(initialEvent?.date ?? '');
    const [proposedStart, setProposedStart] = useState(initialEvent?.startTime ?? '10:00');
    const [proposedEnd, setProposedEnd] = useState(initialEvent?.endTime ?? '16:00');
    const [proposedVenue, setProposedVenue] = useState(initialEvent?.venue ?? '');

    const selectedEvent = editableEvents.find((event) => event.id === selectedId) ?? editableEvents[0];
    const dateChanged = proposedDate !== selectedEvent.date;
    const timeChanged = proposedStart !== selectedEvent.startTime || proposedEnd !== selectedEvent.endTime;
    const venueChanged = proposedVenue !== selectedEvent.venue;
    const changed = dateChanged || timeChanged || venueChanged;
    const holiday = getHolidayForDate(proposedDate);

    const affectedEvents = useMemo(() => {
        if (!proposedDate || !proposedStart || !proposedEnd || minuteOfDay(proposedEnd) <= minuteOfDay(proposedStart)) return [];
        const start = minuteOfDay(proposedStart);
        const end = minuteOfDay(proposedEnd);
        return CAMPUS_CALENDAR_EVENTS.filter((event) => event.id !== selectedEvent.id && event.date === proposedDate).map((event) => {
            const otherStart = minuteOfDay(event.startTime);
            const otherEnd = minuteOfDay(event.endTime);
            const overlaps = start < otherEnd && otherStart < end;
            const gapMinutes = overlaps ? 0 : start >= otherEnd ? start - otherEnd : otherStart - end;
            const sameVenue = proposedVenue.trim().toLowerCase() === event.venue.trim().toLowerCase() && proposedVenue !== 'Venue not selected';
            return { event, overlaps, sameVenue, gapMinutes, gapViolation: gapMinutes < 120 };
        });
    }, [proposedDate, proposedStart, proposedEnd, proposedVenue, selectedEvent.id]);

    const validationMessage = !proposedDate
        ? 'Choose a proposed date to check event and academic-calendar impacts.'
        : minuteOfDay(proposedEnd) <= minuteOfDay(proposedStart)
            ? 'End time must be later than start time.'
            : null;

    const selectEvent = (eventId: string) => {
        const event = editableEvents.find((item) => item.id === eventId);
        if (!event) return;
        setSelectedId(event.id);
        setProposedDate(event.date);
        setProposedStart(event.startTime);
        setProposedEnd(event.endTime);
        setProposedVenue(event.venue);
    };

    const resetScenario = () => {
        setProposedDate(selectedEvent.date);
        setProposedStart(selectedEvent.startTime);
        setProposedEnd(selectedEvent.endTime);
        setProposedVenue(selectedEvent.venue);
    };

    const changeNotes = [
        ...(dateChanged ? ['Date changed: review academic-calendar notes and revalidate catering, travel, and approvals.'] : []),
        ...(timeChanged ? ['Time changed: recheck event spacing and any time-bound support arrangements.'] : []),
        ...(venueChanged ? ['Venue changed: confirm the request through the responsible office and update participant directions.'] : []),
        ...(selectedEvent.support?.length && (dateChanged || timeChanged || venueChanged) ? [`Recheck selected ICTS support (${selectedEvent.support.join(', ')}) against the new details.`] : []),
    ];

    return (
        <div className="space-y-6">
            <section className="border-b border-stone-200 pb-6">
                <div className="grid gap-5 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
                    <div className="min-w-0">
                        <label htmlFor="impact-event" className="block text-xs font-bold uppercase tracking-[0.16em] text-[#7a1b32]">Choose an event to review</label>
                        <select id="impact-event" value={selectedEvent.id} onChange={(event) => selectEvent(event.target.value)} className="mt-2 block w-full rounded-lg border border-stone-300 bg-white px-3 py-3 text-sm font-semibold text-gray-800 outline-none focus:border-[#7a1b32] focus:ring-2 focus:ring-rose-100">
                            {editableEvents.map((event) => <option key={event.id} value={event.id}>{event.title} · {event.club} · {event.date}</option>)}
                        </select>
                        <p className="mt-2 text-xs leading-5 text-gray-500">Scenario events are synthetic fixtures with varied workflow states. Changes are a preview and are not saved.</p>
                    </div>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <label className="text-xs font-bold uppercase tracking-wider text-gray-600">Proposed date
                            <input type="date" value={proposedDate} onChange={(event) => setProposedDate(event.target.value)} className="mt-2 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-sm font-normal normal-case tracking-normal text-gray-800 outline-none focus:border-[#7a1b32]" />
                        </label>
                        <label className="text-xs font-bold uppercase tracking-wider text-gray-600">Proposed venue
                            <select value={proposedVenue} onChange={(event) => setProposedVenue(event.target.value)} className="mt-2 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-sm font-normal normal-case tracking-normal text-gray-800 outline-none focus:border-[#7a1b32]">
                                {['Sandeepani Hall, AB2 Ground Floor', 'Amriteshwari Hall', 'AB-2 Portico', 'Student Computer Lab, AB-2', 'Venue not selected'].map((venue) => <option key={venue}>{venue}</option>)}
                            </select>
                        </label>
                        <label className="text-xs font-bold uppercase tracking-wider text-gray-600">Start time
                            <input type="time" value={proposedStart} onChange={(event) => setProposedStart(event.target.value)} className="mt-2 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-sm font-normal normal-case tracking-normal text-gray-800 outline-none focus:border-[#7a1b32]" />
                        </label>
                        <label className="text-xs font-bold uppercase tracking-wider text-gray-600">End time
                            <input type="time" value={proposedEnd} onChange={(event) => setProposedEnd(event.target.value)} className="mt-2 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-sm font-normal normal-case tracking-normal text-gray-800 outline-none focus:border-[#7a1b32]" />
                        </label>
                    </div>
                </div>
            </section>

            <section className="grid gap-4 lg:grid-cols-2" aria-label="Current and proposed event details">
                <div className="min-w-0 border-l-2 border-stone-300 pl-4">
                    <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-gray-500">Current plan</p>
                    <h2 className="mt-2 break-words text-lg font-bold text-gray-900">{selectedEvent.title}</h2>
                    <p className="mt-1 text-sm text-gray-600">{selectedEvent.club} · {selectedEvent.date}</p>
                    <p className="mt-2 text-sm text-gray-700">{timeLabel(selectedEvent.startTime)}–{timeLabel(selectedEvent.endTime)} · {selectedEvent.venue}</p>
                    <span className="mt-3 inline-flex rounded-full bg-stone-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-stone-700">{statusLabel(selectedEvent)}</span>
                </div>
                <div className="min-w-0 border-l-2 border-[#7a1b32] pl-4">
                    <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#7a1b32]">Proposed plan</p>
                    <h2 className="mt-2 break-words text-lg font-bold text-gray-900">{selectedEvent.title}</h2>
                    <p className="mt-1 text-sm text-gray-600">{selectedEvent.club} · {proposedDate || 'Date not set'}</p>
                    <p className="mt-2 break-words text-sm text-gray-700">{proposedStart ? timeLabel(proposedStart) : '--'}–{proposedEnd ? timeLabel(proposedEnd) : '--'} · {proposedVenue || 'Venue not selected'}</p>
                    {changed ? <button type="button" onClick={resetScenario} className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-[#7a1b32] hover:underline"><RotateCcw className="h-3.5 w-3.5" /> Reset preview</button> : <span className="mt-3 inline-flex rounded-full bg-amber-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-amber-800">No changes yet</span>}
                </div>
            </section>

            {validationMessage ? <p role="alert" className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">{validationMessage}</p> : (
                <section aria-live="polite" className="space-y-5">
                    <div className="flex items-start gap-3 border-l-4 border-amber-400 bg-amber-50/70 px-4 py-3">
                        <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />
                        <div><h2 className="text-sm font-bold text-amber-950">Impact preview · not an approval or booking check</h2><p className="mt-1 text-xs leading-5 text-amber-900">Conflict results are advisory. Core API must recheck constraints when a real event change is submitted; actual venue availability stays unknown.</p></div>
                    </div>
                    {holiday && <div className="flex items-start gap-3 border-l-4 border-red-500 bg-red-50 px-4 py-3"><CalendarDays className="mt-0.5 h-5 w-5 shrink-0 text-red-700" /><div><h3 className="text-sm font-bold text-red-950">Academic calendar holiday on proposed date</h3><p className="mt-1 text-xs leading-5 text-red-900">{holiday.title}. Review institutional operations before proceeding.</p><a href={holiday.sourceUrl} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs font-semibold text-red-900 underline underline-offset-2">View official academic calendar</a></div></div>}
                    <div>
                        <h3 className="flex items-center gap-2 text-sm font-bold text-gray-900"><AlertTriangle className="h-4 w-4 text-amber-600" />Other events on {proposedDate}</h3>
                        {affectedEvents.length ? <div className="mt-3 divide-y divide-stone-200 border-y border-stone-200">{affectedEvents.map(({ event, overlaps, sameVenue, gapMinutes, gapViolation }) => <article key={event.id} className="grid gap-2 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"><div className="min-w-0"><h4 className="break-words text-sm font-semibold text-gray-900">{event.title}</h4><p className="mt-1 text-xs text-gray-600">{event.club} · {timeLabel(event.startTime)}–{timeLabel(event.endTime)} · {event.venue}</p><p className="mt-1 text-[10px] font-semibold uppercase tracking-wider text-gray-500">{statusLabel(event)}</p></div><div className="flex flex-wrap gap-1.5">{overlaps && <span className="rounded-full bg-red-100 px-2 py-1 text-[10px] font-bold text-red-900">Time overlap</span>}{sameVenue && overlaps && <span className="rounded-full bg-red-100 px-2 py-1 text-[10px] font-bold text-red-900">Same venue</span>}{gapViolation && !overlaps && <span className="rounded-full bg-amber-100 px-2 py-1 text-[10px] font-bold text-amber-900">Gap only {gapMinutes} min</span>}{!overlaps && !gapViolation && <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-bold text-emerald-800">No time clash detected</span>}</div></article>)}</div> : <p className="mt-3 border-y border-stone-200 py-4 text-sm text-gray-600">No other fixture events are listed on this date. That does not establish venue availability.</p>}
                    </div>
                    <div>
                        <h3 className="text-sm font-bold text-gray-900">Change-dependent follow-ups</h3>
                        {changeNotes.length ? <ul className="mt-3 space-y-2">{changeNotes.map((note) => <li key={note} className="flex items-start gap-2 text-sm leading-6 text-gray-700"><ArrowRight className="mt-1 h-4 w-4 shrink-0 text-[#7a1b32]" />{note}</li>)}</ul> : <p className="mt-2 text-sm text-gray-600">Edit a field above to see which coordination items may need review.</p>}
                        {selectedEvent.support?.length ? <p className="mt-3 text-xs text-gray-500">Support tagged on this demo event: {selectedEvent.support.join(', ')}.</p> : null}
                    </div>
                </section>
            )}
        </div>
    );
}
