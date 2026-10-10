import {
  AlertTriangle,
  Clock,
  CalendarDays,
  FileCheck,
  Info,
  Book,
  Calendar as CalendarIcon,
  Monitor,
  Building2,
  GraduationCap
} from "lucide-react";

export default function Dashboard() {
  const stats = [
    { label: "overlaps detected", count: 2, icon: AlertTriangle, color: "text-red-600", bg: "bg-red-100" },
    { label: "pending commitments", count: 5, icon: Clock, color: "text-orange-600", bg: "bg-orange-100" },
    { label: "needs revalidation", count: 3, icon: CalendarDays, color: "text-amber-600", bg: "bg-amber-100" },
    { label: "reports due", count: 1, icon: FileCheck, color: "text-blue-600", bg: "bg-blue-100" },
  ];

  const sources = [
    { label: "OSA Handbook", icon: Book, desc: "Guidelines & Rules" },
    { label: "Campus Events", icon: CalendarIcon, desc: "Event Directory" },
    { label: "Academic Calendar", icon: GraduationCap, desc: "Important Dates" },
    { label: "ICTS", icon: Monitor, desc: "Tech Resources" },
    { label: "Facilities", icon: Building2, desc: "Venue Management" },
  ];

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <header className="flex items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Welcome back, Arjun <span className="inline-flex items-center rounded-md bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-800 ring-1 ring-inset ring-yellow-600/20 align-middle ml-2">DEMO DATA</span></h1>
          <p className="text-gray-500 mt-1">Here is what is happening with your events.</p>
        </div>
      </header>

      {/* Hero Card */}
      <section className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-4">
           <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
             Featured Event
           </span>
        </div>
        <h2 className="text-2xl font-bold text-indigo-900 mb-2">INIT AI HACKATHON</h2>
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 text-gray-600 mb-6">
          <div className="flex items-center space-x-2">
            <CalendarIcon className="w-5 h-5 text-indigo-500" />
            <span>Oct 24 - Oct 26, 2026</span>
          </div>
          <div className="hidden sm:block text-gray-300">|</div>
          <div className="flex items-center space-x-2">
            <Building2 className="w-5 h-5 text-indigo-500" />
            <span>Preferred: Acharya Hall (Tentative)</span>
          </div>
        </div>
        
        <div className="flex flex-wrap gap-2">
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 border border-yellow-200">
            Tentative
          </span>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800 border border-orange-200">
            Approval Pending
          </span>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 border border-red-200">
            Hall Unconfirmed
          </span>
        </div>
      </section>

      {/* Stats */}
      <section>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat, idx) => {
            const Icon = stat.icon;
            return (
              <div key={idx} className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 flex items-center space-x-4">
                <div className={`p-3 rounded-lg ${stat.bg}`}>
                  <Icon className={`w-6 h-6 ${stat.color}`} />
                </div>
                <div>
                  <div className="text-2xl font-bold text-gray-900">{stat.count}</div>
                  <div className="text-sm font-medium text-gray-500">{stat.label}</div>
                </div>
              </div>
            );
          })}
        </div>
        
        {/* Yellow Banner */}
        <div className="mt-4 bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-r-md">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <Info className="h-5 w-5 text-yellow-400" aria-hidden="true" />
            </div>
            <div className="ml-3">
              <p className="text-sm text-yellow-700 font-medium">
                Tentative interest is not a hall reservation.
                Please ensure you receive official confirmation from Facilities before announcing venues.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Unified Sources */}
      <section>
        <h3 className="text-xl font-bold text-gray-900 mb-4">Unified Sources</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {sources.map((source, idx) => {
            const Icon = source.icon;
            return (
              <div key={idx} className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 flex flex-col items-center text-center hover:border-indigo-300 transition-colors cursor-pointer">
                <div className="p-3 bg-indigo-50 text-indigo-600 rounded-full mb-3">
                  <Icon className="w-6 h-6" />
                </div>
                <h4 className="font-semibold text-gray-900 text-sm">{source.label}</h4>
                <p className="text-xs text-gray-500 mt-1">{source.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

    </div>
  );
}
