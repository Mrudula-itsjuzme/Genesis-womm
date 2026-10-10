export const ACADEMIC_CALENDAR_SOURCE = 'https://intranet.cb.amrita.edu/2026/calendar/Academic-Calendar-AY-2026-2027.pdf';
export const CAMPUS_EVENTS_SOURCE = 'https://intranet.cb.amrita.edu/events';

export type DemoEventStatus = 'DRAFT' | 'TENTATIVE' | 'SUBMITTED' | 'ACKNOWLEDGED' | 'CONFIRMED' | 'PUBLISHED';

export interface CampusCalendarEvent {
    id: string;
    title: string;
    date: string;
    startTime: string;
    endTime: string;
    venue: string;
    club: string;
    status: DemoEventStatus;
    synthetic: boolean;
    sourceUrl?: string;
    support?: string[];
    note: string;
}

export interface CampusCalendarHoliday {
    id: string;
    title: string;
    date: string;
    sourceUrl: string;
    note: string;
}

export const CAMPUS_CALENDAR_EVENTS: CampusCalendarEvent[] = [
    {
        id: 'published-sadgamaya-2026',
        title: 'Cultural Retreat (Sadgamaya)',
        date: '2026-06-15',
        startTime: '09:00',
        endTime: '17:00',
        venue: 'Amriteshwari Hall',
        club: 'Student Affairs',
        status: 'PUBLISHED',
        synthetic: false,
        sourceUrl: 'https://intranet.cb.amrita.edu/events/2026/Sadgamaya',
        note: 'Published historical campus event. Its venue use does not indicate present or future availability.',
    },
    {
        id: 'published-ingenium-2026',
        title: 'INGENIUM 26',
        date: '2026-09-15',
        startTime: '14:00',
        endTime: '17:00',
        venue: 'Amriteshwari Hall',
        club: 'Association of Mechanical Engineering Students',
        status: 'PUBLISHED',
        synthetic: false,
        sourceUrl: 'https://intranet.cb.amrita.edu/events/2026/INGENIUM26',
        note: 'Published historical campus event. Source gives venue and date, not live booking availability.',
    },
    {
        id: 'published-vinayaka-2026',
        title: 'Vinayaka Vaibhavam',
        date: '2026-09-16',
        startTime: '16:00',
        endTime: '19:00',
        venue: 'AB-2 Portico',
        club: 'Student Affairs',
        status: 'PUBLISHED',
        synthetic: false,
        sourceUrl: 'https://intranet.cb.amrita.edu/events/2026/Vinayaka-Vaibhavam',
        note: 'Published historical campus event. Source gives venue and date, not live booking availability.',
    },
    {
        id: 'published-amma-talks-2026',
        title: 'Amma Talks',
        date: '2026-09-22',
        startTime: '17:00',
        endTime: '18:00',
        venue: 'Sandeepani Hall, AB2 Ground Floor',
        club: 'Sadhana Club',
        status: 'PUBLISHED',
        synthetic: false,
        sourceUrl: 'https://intranet.cb.amrita.edu/events/2026/Amma_Talks',
        note: 'Published historical campus event. Source gives venue and date, not live booking availability.',
    },
    {
        id: 'demo-initiative-hackathon',
        title: 'INIT AI Hackathon',
        date: '2026-10-13',
        startTime: '10:00',
        endTime: '16:00',
        venue: 'Sandeepani Hall, AB2 Ground Floor',
        club: 'AI Club',
        status: 'TENTATIVE',
        synthetic: true,
        support: ['audiovisual'],
        note: 'Synthetic CampusCue planning scenario; not an official campus event or venue booking.',
    },
    {
        id: 'demo-robotics-challenge',
        title: 'Robotics Build Challenge',
        date: '2026-10-13',
        startTime: '14:00',
        endTime: '17:00',
        venue: 'Sandeepani Hall, AB2 Ground Floor',
        club: 'Robotics Club',
        status: 'SUBMITTED',
        synthetic: true,
        support: ['audiovisual'],
        note: 'Synthetic submitted-state example; submission is not acknowledgment or approval.',
    },
    {
        id: 'demo-media-workshop',
        title: 'Campus Storytelling Workshop',
        date: '2026-10-17',
        startTime: '11:00',
        endTime: '13:00',
        venue: 'AB-2 Portico',
        club: 'Team Media',
        status: 'ACKNOWLEDGED',
        synthetic: true,
        note: 'Synthetic acknowledged-state example; acknowledgment is not confirmation.',
    },
    {
        id: 'demo-data-sprint',
        title: 'Data for Good Sprint',
        date: '2026-10-20',
        startTime: '09:30',
        endTime: '12:30',
        venue: 'Student Computer Lab, AB-2',
        club: 'School of Computing Student Community',
        status: 'DRAFT',
        synthetic: true,
        support: ['lab-scheduling', 'wifi'],
        note: 'Synthetic draft-state example; a preferred lab remains subject to official allocation.',
    },
    {
        id: 'demo-sadhana-session',
        title: 'Mindful Campus Session',
        date: '2026-10-22',
        startTime: '16:00',
        endTime: '17:30',
        venue: 'Amriteshwari Hall',
        club: 'Sadhana Club',
        status: 'CONFIRMED',
        synthetic: true,
        note: 'Synthetic confirmed-state fixture for UI testing only; it is not an official reservation.',
    },
    {
        id: 'demo-design-expo',
        title: 'Design for Campus Expo',
        date: '2026-11-03',
        startTime: '13:00',
        endTime: '17:00',
        venue: 'Amriteshwari Hall',
        club: 'Design Club',
        status: 'TENTATIVE',
        synthetic: true,
        note: 'Synthetic CampusCue planning scenario; not an official campus event or venue booking.',
    },
    {
        id: 'demo-open-source-day',
        title: 'Open Source Day',
        date: '2026-11-05',
        startTime: '10:00',
        endTime: '15:00',
        venue: 'Venue not selected',
        club: 'FOSS Community',
        status: 'SUBMITTED',
        synthetic: true,
        note: 'Synthetic submitted-state example; submission is not acknowledgment or approval.',
    },
    {
        id: 'demo-cultural-night',
        title: 'Inter-Club Cultural Night',
        date: '2026-11-12',
        startTime: '17:00',
        endTime: '20:00',
        venue: 'Amriteshwari Hall',
        club: 'Campus Arts Collective',
        status: 'ACKNOWLEDGED',
        synthetic: true,
        support: ['audiovisual'],
        note: 'Synthetic acknowledged-state example; acknowledgment is not confirmation.',
    },
];

export const CAMPUS_CALENDAR_HOLIDAYS: CampusCalendarHoliday[] = [
    {
        id: 'muharram-2026',
        title: 'Holiday · Muharram',
        date: '2026-06-26',
        sourceUrl: ACADEMIC_CALENDAR_SOURCE,
        note: 'Named holiday shown on the official Academic Calendar AY 2026–27.',
    },
];

export function getWeeklyHoliday(date: string): CampusCalendarHoliday | null {
    const [year, month, day] = date.split('-').map(Number);
    const campusDate = new Date(Date.UTC(year, month - 1, day));
    const inAcademicYear = date >= '2026-06-01' && date <= '2027-06-30';
    if (!inAcademicYear || campusDate.getUTCDay() !== 0) return null;
    return {
        id: `sunday-holiday-${date}`,
        title: 'Weekly holiday',
        date,
        sourceUrl: ACADEMIC_CALENDAR_SOURCE,
        note: 'Sunday is marked Holiday in the official Academic Calendar AY 2026–27.',
    };
}

export function getHolidayForDate(date: string): CampusCalendarHoliday | null {
    return CAMPUS_CALENDAR_HOLIDAYS.find((holiday) => holiday.date === date) ?? getWeeklyHoliday(date);
}