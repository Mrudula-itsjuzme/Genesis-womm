'use client';

import { useState, useSyncExternalStore } from 'react';
import { ArrowLeft, ArrowRight, CalendarDays, ChevronDown, Clock3, MapPin } from 'lucide-react';
import Link from 'next/link';
import { ACADEMIC_CALENDAR_SOURCE, CAMPUS_CALENDAR_EVENTS, CAMPUS_EVENTS_SOURCE, getHolidayForDate, type CampusCalendarEvent } from '@/lib/campus-calendar-data';

type ViewMode = 'Month' | 'Week' | 'List';

const dateKey = (date: Date) => `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}-${String(date.getUTCDate()).padStart(2, '0')}`;
const dateFromKey = (key: string) => {
    const [year, month, day] = key.split('-').map(Number);
    return new Date(Date.UTC(year, month - 1, day));
};
const formatDate = (date: Date, options: Intl.DateTimeFormatOptions = { dateStyle: 'full' }) => new Intl.DateTimeFormat('en-IN', { ...options, timeZone: 'Asia/Kolkata' }).format(date);
const subscribeToDate = () => () => { };
const getCurrentDateKey = () => {
    const parts = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
    const part = (type: Intl.DateTimeFormatPartTypes) => parts.find((item) => item.type === type)?.value ?? '';
    return `${part('year')}-${part('month')}-${part('day')}`;
};
const getServerDateKey = () => '2000-01-01';

const statusStyles: Record<CampusCalendarEvent['status'], string> = {
    DRAFT: 'bg-rose-100 text-rose-900',
    TENTATIVE: 'bg-amber-100 text-amber-900',
    SUBMITTED: 'bg-blue-100 text-blue-900',
    ACKNOWLEDGED: 'bg-indigo-100 text-indigo-900',
    CONFIRMED: 'bg-emerald-100 text-emerald-900',
    PUBLISHED: 'bg-stone-200 text-stone-800',
};

const statusLabel = (status: CampusCalendarEvent['status']) => status === 'PUBLISHED' ? 'Published' : status === 'DRAFT' ? 'Draft' : status[0] + status.slice(1).toLowerCase();
const formatTime = (time: string) => {
    const [hourText, minute] = time.split(':');
    const hour = Number(hourText);
    return `${hour % 12 || 12}:${minute} ${hour < 12 ? 'AM' : 'PM'}`;
};

export default function CalendarGrid() {
    const currentDateKey = useSyncExternalStore(subscribeToDate, getCurrentDateKey, getServerDateKey);
    const today = dateFromKey(currentDateKey);
    const [selectedDateKey, setSelectedDateKey] = useState<string | null>(null);
    const selectedDate = dateFromKey(selectedDateKey ?? currentDateKey);
    const events = CAMPUS_CALENDAR_EVENTS;
    const [activeView, setActiveView] = useState<ViewMode>('Month');
    const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

    const year = selectedDate.getUTCFullYear();
    const month = selectedDate.getUTCMonth();
    const monthStart = new Date(Date.UTC(year, month, 1));
    const monthEnd = new Date(Date.UTC(year, month + 1, 0));
    const monthDates = Array.from({ length: Math.ceil((monthStart.getUTCDay() + monthEnd.getUTCDate()) / 7) * 7 }, (_, index) => new Date(Date.UTC(year, month, index - monthStart.getUTCDay() + 1)));
    const weekStart = new Date(Date.UTC(year, month, selectedDate.getUTCDate() - selectedDate.getUTCDay()));
    const weekDates = Array.from({ length: 7 }, (_, index) => new Date(Date.UTC(weekStart.getUTCFullYear(), weekStart.getUTCMonth(), weekStart.getUTCDate() + index)));
    const visibleDates = activeView === 'Week' ? weekDates : monthDates;
    const selectedKey = dateKey(selectedDate);
    const selectedDayEvents = events.filter((event) => event.date === selectedKey);
    const selectedEvent = selectedDayEvents.find((event) => event.id === selectedEventId);
    const selectedHoliday = getHolidayForDate(selectedKey);
    const selectedMonthEvents = events.filter((event) => event.date.startsWith(`${year}-${String(month + 1).padStart(2, '0')}`)).sort((a, b) => a.date.localeCompare(b.date));

    const selectMonthYear = (nextYear: number, nextMonth: number) => {
        const lastDay = new Date(Date.UTC(nextYear, nextMonth + 1, 0)).getUTCDate();
        updateDate(new Date(Date.UTC(nextYear, nextMonth, Math.min(selectedDate.getUTCDate(), lastDay))));
    };

    const updateDate = (date: Date) => {
        setSelectedDateKey(dateKey(date));
        setSelectedEventId(null);
    };
    const changePeriod = (offset: number) => {
        if (activeView === 'Week') {
            const nextDate = new Date(selectedDate);
            nextDate.setDate(nextDate.getDate() + offset * 7);
            updateDate(nextDate);
            return;
        }
        const nextMonth = new Date(Date.UTC(selectedDate.getUTCFullYear(), selectedDate.getUTCMonth() + offset, 1));
        const lastDay = new Date(Date.UTC(nextMonth.getUTCFullYear(), nextMonth.getUTCMonth() + 1, 0)).getUTCDate();
        updateDate(new Date(Date.UTC(nextMonth.getUTCFullYear(), nextMonth.getUTCMonth(), Math.min(selectedDate.getUTCDate(), lastDay))));
    };

    const renderDay = (date: Date) => {
        const key = dateKey(date);
        const isSelected = key === selectedKey;
        const isToday = key === dateKey(today);
        const isOutsideMonth = date.getUTCMonth() !== month;
        const dayEvents = events.filter((event) => event.date === key);
        const holiday = getHolidayForDate(key);
        return (
            <div key={key} className={`min-w-0 border-b border-r border-stone-100 p-1.5 sm:p-2 ${isSelected ? 'bg-rose-50/80' : 'bg-white'} ${isOutsideMonth && activeView === 'Month' ? 'opacity-55' : ''}`}>
                <button type="button" onClick={() => updateDate(date)} aria-label={`Show events for ${formatDate(date)}`} aria-pressed={isSelected} className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-colors sm:h-9 sm:w-9 ${isSelected ? 'bg-[#7a1b32] text-white' : isToday ? 'border border-[#7a1b32] text-[#7a1b32]' : 'text-gray-700 hover:bg-rose-100'}`}>
                    {date.getUTCDate()}
                </button>
                <div className="mt-1 space-y-1">
                    {dayEvents.slice(0, 2).map((event) => (
                        <button key={event.id} type="button" onClick={() => { updateDate(date); setSelectedEventId(event.id); }} className={`w-full truncate rounded-md px-1.5 py-1 text-left text-[9px] font-bold leading-tight sm:px-2 sm:text-[10px] ${statusStyles[event.status]}`} title={`${event.title} · ${statusLabel(event.status)}${event.synthetic ? ' · synthetic demo' : ''}`}>
                            <span className="hidden sm:inline">{event.title}</span><span className="sm:hidden">{event.title.split(' ')[0]}</span>
                        </button>
                    ))}
                    {dayEvents.length > 2 && <span className="block px-1 text-[9px] text-gray-500">+{dayEvents.length - 2}</span>}
                    {holiday && <span title={holiday.note} className="block truncate rounded-md bg-red-50 px-1.5 py-1 text-[9px] font-bold leading-tight text-red-800 sm:px-2 sm:text-[10px]">{holiday.title}</span>}
                </div>
            </div>
        );
    };

    return (
        <div className="mt-16 flex min-h-[calc(100dvh-4rem)] min-w-0 flex-col bg-[#F5EEE9] xl:flex-row">
            <main className="min-w-0 flex-1 px-4 py-5 sm:px-6 lg:px-8">
                <div className="mx-auto max-w-[1400px]">
                    <header className="mb-5 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                        <div>
                            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#7a1b32]">Campus schedule</p>
                            <h1 className="mt-2 text-3xl font-bold tracking-tight text-gray-900">Calendar</h1>
                            <p className="mt-1 text-sm text-gray-600">Published past notices and synthetic planning examples are shown separately.</p>
                            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs font-semibold">
                                <a href={CAMPUS_EVENTS_SOURCE} target="_blank" rel="noreferrer" className="text-[#7a1b32] underline underline-offset-2">Published campus event notices</a>
                                <a href={ACADEMIC_CALENDAR_SOURCE} target="_blank" rel="noreferrer" className="text-[#7a1b32] underline underline-offset-2">Official AY 2026–27 calendar</a>
                            </div>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            <button type="button" onClick={() => updateDate(new Date(today))} className="rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-gray-700 hover:border-rose-300">Today</button>
                            <div className="flex items-center rounded-lg border border-stone-200 bg-white">
                                <button type="button" aria-label="Previous month or week" onClick={() => changePeriod(-1)} className="p-2 text-gray-600 hover:text-[#7a1b32]"><ArrowLeft className="h-4 w-4" /></button>
                                <button type="button" aria-label="Next month or week" onClick={() => changePeriod(1)} className="p-2 text-gray-600 hover:text-[#7a1b32]"><ArrowRight className="h-4 w-4" /></button>
                            </div>
                            <label className="relative"><span className="sr-only">Select month</span>
                                <select value={month} onChange={(event) => selectMonthYear(year, Number(event.target.value))} className="appearance-none rounded-lg border border-stone-200 bg-white py-2 pl-3 pr-8 text-sm font-semibold text-gray-800">
                                    {Array.from({ length: 12 }, (_, index) => <option key={index} value={index}>{new Intl.DateTimeFormat('en', { month: 'long', timeZone: 'Asia/Kolkata' }).format(new Date(Date.UTC(2020, index, 1)))}</option>)}
                                </select><ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
                            </label>
                            <label className="relative"><span className="sr-only">Select year</span>
                                <select value={year} onChange={(event) => selectMonthYear(Number(event.target.value), month)} className="appearance-none rounded-lg border border-stone-200 bg-white py-2 pl-3 pr-8 text-sm font-semibold text-gray-800">
                                    {Array.from({ length: 9 }, (_, index) => today.getFullYear() - 4 + index).map((optionYear) => <option key={optionYear} value={optionYear}>{optionYear}</option>)}
                                </select><ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
                            </label>
                        </div>
                    </header>

                    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                        <h2 className="text-xl font-bold text-gray-900" aria-live="polite">{activeView === 'Week' ? `${formatDate(weekDates[0], { month: 'short', day: 'numeric' })} - ${formatDate(weekDates[6], { month: 'short', day: 'numeric', year: 'numeric' })}` : formatDate(selectedDate, { month: 'long', year: 'numeric' })}</h2>
                        <div className="inline-flex rounded-lg border border-stone-200 bg-white p-1" role="group" aria-label="Calendar view">
                            {(['Month', 'Week', 'List'] as ViewMode[]).map((view) => <button key={view} type="button" onClick={() => setActiveView(view)} aria-pressed={activeView === view} className={`rounded-md px-3 py-1.5 text-xs font-bold ${activeView === view ? 'bg-[#7a1b32] text-white' : 'text-gray-600 hover:bg-rose-50'}`}>{view}</button>)}
                        </div>
                    </div>

                    {activeView === 'List' ? (
                        <section aria-label="Events this month" className="space-y-2">
                            {selectedMonthEvents.length ? selectedMonthEvents.map((event) => <button key={event.id} type="button" onClick={() => { updateDate(dateFromKey(event.date)); setSelectedEventId(event.id); }} className="flex w-full flex-col gap-2 rounded-xl border border-stone-200 bg-white p-4 text-left hover:border-rose-300 sm:flex-row sm:items-center sm:justify-between"><span className="min-w-0"><span className="block font-semibold text-gray-900">{event.title}</span><span className="text-xs text-gray-500">{event.club} · {event.venue}</span></span><span className="flex shrink-0 items-center gap-2 text-sm text-gray-600">{formatDate(dateFromKey(event.date), { weekday: 'short', month: 'short', day: 'numeric' })} · {formatTime(event.startTime)} <span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase ${statusStyles[event.status]}`}>{statusLabel(event.status)}{event.synthetic ? ' · demo' : ''}</span></span></button>) : <p className="rounded-xl border border-stone-200 bg-white p-6 text-sm text-gray-600">No listed events in this month.</p>}
                        </section>
                    ) : (
                        <section aria-label={`${activeView} calendar`} className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm">
                            <div className="grid grid-cols-7 border-b border-stone-100 bg-[#FFF5F0]">{['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => <div key={day} className="py-2 text-center text-[10px] font-bold uppercase tracking-wider text-[#7a1b32] sm:py-3 sm:text-xs">{day}</div>)}</div>
                            <div className={`grid grid-cols-7 ${activeView === 'Month' ? 'auto-rows-[minmax(78px,auto)] sm:auto-rows-[minmax(110px,auto)]' : 'auto-rows-[minmax(150px,auto)]'}`}>{visibleDates.map(renderDay)}</div>
                        </section>
                    )}
                    <p className="mt-3 text-xs text-gray-500">Synthetic event statuses are for scenario testing only. Tentative proposals are not bookings; venue availability remains unknown until confirmed by an authorized office.</p>
                </div>
            </main>

            <aside className="w-full shrink-0 border-t border-stone-200 bg-white/80 p-5 xl:sticky xl:top-16 xl:h-[calc(100dvh-4rem)] xl:w-[360px] xl:overflow-y-auto xl:border-l xl:border-t-0 xl:p-6">
                <div className="flex items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-[#7a1b32]">Selected day</p><h2 className="mt-1 text-lg font-bold text-gray-900">{formatDate(selectedDate)}</h2></div><CalendarDays className="h-5 w-5 text-[#7a1b32]" /></div>
                {selectedHoliday && <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3"><p className="text-sm font-bold text-red-900">{selectedHoliday.title}</p><p className="mt-1 text-xs leading-5 text-red-800">{selectedHoliday.note}</p><a href={selectedHoliday.sourceUrl} target="_blank" rel="noreferrer" className="mt-2 inline-block text-xs font-semibold text-red-900 underline underline-offset-2">Open academic calendar</a></div>}
                <div className="mt-5 space-y-2">
                    {selectedDayEvents.length ? selectedDayEvents.map((event) => <button key={event.id} type="button" onClick={() => setSelectedEventId(event.id)} aria-pressed={selectedEventId === event.id} className={`w-full rounded-xl border p-3 text-left transition-colors ${selectedEventId === event.id ? 'border-[#7a1b32] bg-rose-50' : 'border-stone-200 bg-white hover:border-rose-300'}`}><span className="block text-sm font-bold text-gray-900">{event.title}</span><span className="mt-1 block text-xs text-gray-600">{formatTime(event.startTime)}–{formatTime(event.endTime)} · {event.club}</span></button>) : <p className="rounded-xl border border-dashed border-stone-300 bg-white p-4 text-sm text-gray-500">No events on this day.</p>}
                </div>
                {selectedEvent && <section className="mt-5 rounded-xl border border-rose-100 bg-[#fffaf8] p-4" aria-label="Selected event details"><span className={`inline-flex rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${statusStyles[selectedEvent.status]}`}>{statusLabel(selectedEvent.status)}{selectedEvent.synthetic ? ' · synthetic demo' : ' · published notice'}</span><h3 className="mt-3 text-base font-bold text-gray-900">{selectedEvent.title}</h3><p className="mt-2 flex items-center gap-2 text-sm text-gray-600"><Clock3 className="h-4 w-4 shrink-0" />{formatTime(selectedEvent.startTime)}–{formatTime(selectedEvent.endTime)}</p><p className="mt-2 flex items-center gap-2 text-sm text-gray-600"><MapPin className="h-4 w-4 shrink-0" />{selectedEvent.venue}</p><p className="mt-2 text-sm text-gray-600">Club: {selectedEvent.club}</p><p className="mt-3 border-t border-rose-100 pt-3 text-xs leading-5 text-gray-600">{selectedEvent.note}</p>{selectedEvent.sourceUrl && <a href={selectedEvent.sourceUrl} target="_blank" rel="noreferrer" className="mt-3 inline-block text-xs font-semibold text-[#7a1b32] underline underline-offset-2">Open published source</a>}<Link href="/changes" className="mt-3 block text-xs font-bold text-[#7a1b32] underline underline-offset-2">Review change impact</Link></section>}
            </aside>
        </div>
    );
}