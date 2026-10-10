import Link from 'next/link';
import { ArrowLeft, MapPinned } from 'lucide-react';
import { ResourceCard, type ResourceProps } from '@/components/ResourceCard';

const venues: ResourceProps[] = [
    { id: 'amriteshwari-hall', name: 'Amriteshwari Hall', type: 'Hall', location: 'Location details not stated on the event notice', responsibleOffice: 'Confirm with responsible campus office', availabilityStatus: 'unknown', source: 'Official campus event notice', sourceUrl: 'https://intranet.cb.amrita.edu/events/2026/INGENIUM26', description: 'Published as the venue for INGENIUM ’26 on 15 September 2026. This is a past event location, not current availability.' },
    { id: 'sandeepani-hall', name: 'Sandeepani Hall', type: 'Hall', location: 'AB2, Ground Floor', responsibleOffice: 'Confirm with responsible campus office', availabilityStatus: 'unknown', source: 'Official campus event notice', sourceUrl: 'https://intranet.cb.amrita.edu/events/2026/Amma_Talks', description: 'Published as the venue for Amma Talks on 22 September 2026. This is a past event location, not current availability.' },
    { id: 'ab2-portico', name: 'AB-2 Portico', type: 'Covered open space', location: 'AB-2', responsibleOffice: 'Confirm with responsible campus office', availabilityStatus: 'unknown', source: 'Official campus event notice', sourceUrl: 'https://intranet.cb.amrita.edu/events/2026/Vinayaka-Vaibhavam', description: 'Published as the venue for Vinayaka Vaibhavam on 16 September 2026. This is a past event location, not current availability.' },
    { id: 'ab1-shrine-area', name: 'AB1, behind the Saraswati statue', type: 'Campus area', location: 'AB1, behind the Saraswati statue', responsibleOffice: 'Confirm with responsible campus office', availabilityStatus: 'unknown', source: 'Official campus event notice', sourceUrl: 'https://intranet.cb.amrita.edu/events/2026/Vishnu-Sadhana', description: 'Published as the location for Vishnu Sadhana beginning 7 September 2026. This is a past event location, not current availability.' },
    { id: 'student-computer-labs', name: 'Student Computer Labs', type: 'Computer labs', location: 'Published rooms include AB-1 W-109, AB-1 C-102, and AB-2 D-301/D-302', responsibleOffice: 'ICTS', availabilityStatus: 'unknown', source: 'ICTS infrastructure and services', sourceUrl: 'https://intranet.cb.amrita.edu/infrastructure/icts', description: 'ICTS publishes lab access and timetable information. Event lab allocation requires a separate request.' },
];

export default function VenuesPage() {
    return (
        <div className="mt-16 min-h-[calc(100vh-4rem)] bg-[#F5EEE9] px-5 py-7 sm:px-8 lg:px-10">
            <div className="mx-auto max-w-7xl">
                <Link href="/resources" className="inline-flex items-center gap-2 text-sm font-semibold text-[#7a1b32] hover:text-[#541224]"><ArrowLeft className="h-4 w-4" />Resource library</Link>
                <header className="mb-7 mt-5 flex flex-col gap-4 border-b border-rose-200/70 pb-6 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                        <div className="flex items-center gap-2 text-[#7a1b32]"><MapPinned className="h-5 w-5" /><p className="text-xs font-bold uppercase tracking-[0.18em]">Source-backed examples</p></div>
                        <h1 className="mt-2 text-3xl font-bold tracking-tight text-gray-900">Explore Venues</h1>
                        <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">Examples come from published campus event notices and ICTS information. This is not a complete facilities catalog.</p>
                    </div>
                    <p className="max-w-sm rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-900">Availability is unknown. A past event location does not mean a venue is currently available or booked.</p>
                </header>
                <section aria-label="Published venue examples" className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                    {venues.map((venue) => (
                        <ResourceCard key={venue.id} resource={venue} />
                    ))}
                </section>
            </div>
        </div>
    );
}