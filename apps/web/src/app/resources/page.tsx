import { ExternalLink, FileText, Landmark, CalendarDays, Users, Wifi, BookOpenCheck } from 'lucide-react';

const sourceGroups = [
  {
    title: 'Policies & event procedures',
    icon: BookOpenCheck,
    sources: [
      { name: 'OSA Student Affairs Handbook', url: 'https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf', caption: 'Student event procedures, club processes, facility request material, and activity reporting examples.' },
      { name: 'Student Affairs and Welfare', url: 'https://intranet.cb.amrita.edu/students-affairs-welfare', caption: 'Published student-affairs and club-oversight guidance. Check the page for current instructions.' },
    ],
  },
  {
    title: 'Campus events & venues',
    icon: Landmark,
    sources: [
      { name: 'Coimbatore campus events', url: 'https://intranet.cb.amrita.edu/events', caption: 'Published campus event notices. Venue names show past event locations, not current availability.' },
      { name: 'Coimbatore infrastructure directory', url: 'https://www.amrita.edu/campus/coimbatore/infrastructure/', caption: 'Listed in the source registry, but currently redirects outside the university domain. Verify the destination before relying on it.' },
    ],
  },
  {
    title: 'Academic calendars',
    icon: CalendarDays,
    sources: [
      { name: 'Academic calendar and timetable links', url: 'https://intranet.cb.amrita.edu/academics/calendar', caption: 'Academic-year calendar PDFs and links to student class timetable resources.' },
      { name: 'Official campus calendar feed', url: 'https://outlook.office365.com/owa/calendar/c5368a2f38a14425b7bfe0806e6a7242@amrita.edu/c90d8c3dd3654d4fa7af29ce6c6319907829757625615220928/calendar.ics', caption: 'Published calendar feed. It is not an authoritative venue-booking feed.' },
    ],
  },
  {
    title: 'ICTS services & contacts',
    icon: Wifi,
    sources: [
      { name: 'ICTS infrastructure and services', url: 'https://intranet.cb.amrita.edu/infrastructure/icts', caption: 'Computing labs, network services, audiovisual support, and campus ICT infrastructure.' },
      { name: 'ICTS support contacts', url: 'https://intranet.cb.amrita.edu/infrastructure/icts/support-contacts', caption: 'Published service request routes, including audiovisual and computer-lab scheduling contacts.' },
    ],
  },
  {
    title: 'Clubs & student activities',
    icon: Users,
    sources: [
      { name: 'Coimbatore student clubs', url: 'https://www.amrita.edu/campus/coimbatore/students-club/', caption: 'Club discovery and activity context. Historical or undated information may need verification.' },
      { name: 'School of Computing student corner', url: 'https://www.amrita.edu/school/computing/coimbatore/student-corner/', caption: 'Computing-school clubs and student activities.' },
      { name: 'Life at Amrita', url: 'https://www.amrita.edu/life-at-amrita/', caption: 'General campus life and club information; not every item is Coimbatore-specific.' },
    ],
  },
];

export default function ResourcesPage() {
  return (
    <div className="mt-16 min-h-[calc(100vh-4rem)] bg-[#F5EEE9] px-5 py-7 sm:px-8 lg:px-10">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 border-b border-rose-200/70 pb-6">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#7a1b32]">Campus reference library</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-gray-900">Resources</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-600">
            Official documents and campus websites, grouped by what they contain. Sources do not confirm approvals, bookings, or live availability.
          </p>
        </header>

        <div className="space-y-8">
          {sourceGroups.map((group) => {
            const Icon = group.icon;
            return (
              <section key={group.title} aria-label={group.title}>
                <div className="mb-3 flex items-center gap-2 text-[#7a1b32]">
                  <Icon className="h-4 w-4" />
                  <h2 className="text-sm font-bold uppercase tracking-[0.14em]">{group.title}</h2>
                </div>
                <div className="divide-y divide-stone-200 border-y border-stone-200 bg-white">
                  {group.sources.map((source) => (
                    <article key={source.url} className="flex min-w-0 flex-col gap-2 px-4 py-4 sm:flex-row sm:items-start sm:justify-between sm:gap-6 sm:px-5">
                      <div className="min-w-0">
                        <h3 className="flex items-center gap-2 text-sm font-bold text-gray-900">
                          <FileText className="h-4 w-4 shrink-0 text-[#7a1b32]" />
                          {source.name}
                        </h3>
                        <p className="mt-1 pl-6 text-sm leading-6 text-gray-600">{source.caption}</p>
                      </div>
                      <a href={source.url} target="_blank" rel="noreferrer" className="inline-flex shrink-0 items-center gap-1.5 pl-6 text-xs font-bold text-[#7a1b32] underline decoration-rose-200 underline-offset-2 hover:text-[#541224] sm:pl-0">
                        Open source <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
                        <span className="sr-only"> (opens in a new tab)</span>
                      </a>
                    </article>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      </div>
    </div>
  );
}
