'use client';

import { MessageSquareText, FileText, Search, Sparkles, ArrowUpRight, ShieldCheck } from 'lucide-react';

const promptSuggestions = [
    'What approvals are needed for an intercollege hackathon?',
    'Can a tentative event be advertised before venue confirmation?',
    'Which documents govern guest faculty support for campus events?',
];

const evidenceCards = [
    {
        title: 'OSA Handbook',
        section: 'Section 4.2',
        summary: 'Intercollege events require written permission and faculty sponsor sign-off before scheduling.',
        badge: 'Policy',
    },
    {
        title: 'Facilities Booking Rules',
        section: 'Section 2.1',
        summary: 'Major halls are only confirmed after documentation and approval by the responsible office.',
        badge: 'Venue',
    },
    {
        title: 'Campus Security Guidelines',
        section: 'Section 7.3',
        summary: 'Guest participant lists and security coordination are required for external participation.',
        badge: 'Ops',
    },
];

export default function PolicyPage() {
    return (
        <div className="min-h-screen bg-[#F5EEE9] px-6 py-8 lg:px-10">
            <div className="mx-auto max-w-7xl space-y-8">
                <header className="flex flex-col gap-4 rounded-[28px] bg-white p-6 shadow-[0_8px_25px_rgba(122,27,50,0.06)] ring-1 ring-[#f0e1dc] lg:flex-row lg:items-center lg:justify-between">
                    <div>
                        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#7a1b32]">Campus policy</p>
                        <h1 className="mt-2 text-3xl font-bold tracking-tight text-gray-900">Policy Assistant</h1>
                    </div>
                    <div className="inline-flex items-center gap-2 rounded-full bg-[#fff5f0] px-4 py-2 text-sm font-semibold text-[#7a1b32] ring-1 ring-[#f6dfe3]">
                        <ShieldCheck className="h-4 w-4" />
                        Verified source-grounded answers
                    </div>
                </header>

                <div className="grid gap-8 lg:grid-cols-[1.3fr_0.7fr]">
                    <section className="rounded-[28px] bg-white p-6 shadow-[0_8px_25px_rgba(122,27,50,0.06)] ring-1 ring-[#f0e1dc]">
                        <div className="flex items-center gap-2 text-[#7a1b32]">
                            <MessageSquareText className="h-5 w-5" />
                            <p className="text-sm font-bold uppercase tracking-[0.16em]">Ask CampusCue</p>
                        </div>

                        <div className="mt-6 rounded-2xl border border-[#f0e1dc] bg-[#fdf9f7] p-3">
                            <div className="flex items-center gap-3 rounded-xl border border-[#f7e5e8] bg-white px-4 py-3 shadow-sm">
                                <Search className="h-4 w-4 text-gray-400" />
                                <input
                                    aria-label="Policy question"
                                    className="w-full border-0 bg-transparent text-sm text-gray-700 placeholder:text-gray-400 focus:outline-none"
                                    defaultValue="What approvals are needed for an intercollege hackathon?"
                                />
                            </div>
                        </div>

                        <div className="mt-5 flex flex-wrap gap-2">
                            {promptSuggestions.map((prompt) => (
                                <button
                                    key={prompt}
                                    className="rounded-full border border-[#f1d7dd] bg-[#fffaf8] px-3 py-2 text-xs font-semibold text-[#7a1b32] transition hover:border-[#e7b8c3] hover:bg-[#fff3f3]"
                                >
                                    {prompt}
                                </button>
                            ))}
                        </div>

                        <div className="mt-8 rounded-[24px] border border-[#f0e1dc] bg-gradient-to-br from-[#fff9f7] to-[#fff8f2] p-5">
                            <div className="flex items-center gap-2 text-[#7a1b32]">
                                <Sparkles className="h-4 w-4" />
                                <span className="text-xs font-bold uppercase tracking-[0.16em]">Answer</span>
                            </div>

                            <p className="mt-4 text-sm leading-7 text-gray-700">
                                Based on the current policy corpus, an intercollege hackathon generally needs prior written approval,
                                faculty sponsorship, venue clearance, and operational coordination for security and ICTS support.
                                CampusCue treats the event as tentative until the responsible office confirms the booking.
                            </p>

                            <div className="mt-5 space-y-3">
                                <div className="rounded-2xl border border-[#f3dfe4] bg-white p-3">
                                    <div className="flex items-center justify-between gap-3">
                                        <div className="flex items-center gap-2">
                                            <FileText className="h-4 w-4 text-[#7a1b32]" />
                                            <span className="text-sm font-semibold text-gray-800">OSA Handbook</span>
                                        </div>
                                        <span className="rounded-full bg-[#fff5f0] px-2 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-[#7a1b32]">
                                            Section 4.2
                                        </span>
                                    </div>
                                    <p className="mt-2 text-sm text-gray-600">Approval is required before public scheduling or external participant outreach.</p>
                                </div>

                                <div className="rounded-2xl border border-[#f3dfe4] bg-white p-3">
                                    <div className="flex items-center justify-between gap-3">
                                        <div className="flex items-center gap-2">
                                            <FileText className="h-4 w-4 text-[#7a1b32]" />
                                            <span className="text-sm font-semibold text-gray-800">Security Guidelines</span>
                                        </div>
                                        <span className="rounded-full bg-[#fff5f0] px-2 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-[#7a1b32]">
                                            Section 7.3
                                        </span>
                                    </div>
                                    <p className="mt-2 text-sm text-gray-600">External guest list and security arrangements must be coordinated in advance.</p>
                                </div>
                            </div>
                        </div>
                    </section>

                    <aside className="space-y-6">
                        <div className="rounded-[28px] bg-white p-5 shadow-[0_8px_25px_rgba(122,27,50,0.06)] ring-1 ring-[#f0e1dc]">
                            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#7a1b32]">Evidence</p>
                            <div className="mt-5 space-y-4">
                                {evidenceCards.map((card) => (
                                    <div key={card.title} className="rounded-2xl border border-[#f4e6e2] bg-[#fffaf8] p-4">
                                        <div className="flex items-center justify-between gap-2">
                                            <span className="text-sm font-semibold text-gray-900">{card.title}</span>
                                            <span className="rounded-full bg-[#fff5f0] px-2 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-[#7a1b32]">
                                                {card.badge}
                                            </span>
                                        </div>
                                        <p className="mt-2 text-[11px] font-bold uppercase tracking-[0.14em] text-gray-500">{card.section}</p>
                                        <p className="mt-2 text-sm leading-6 text-gray-600">{card.summary}</p>
                                        <button className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-[#7a1b32]">
                                            View source <ArrowUpRight className="h-3.5 w-3.5" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="rounded-[28px] bg-[#7a1b32] p-5 text-white shadow-[0_8px_25px_rgba(122,27,50,0.24)]">
                            <p className="text-xs font-bold uppercase tracking-[0.18em] text-rose-100">Reminders</p>
                            <ul className="mt-4 space-y-3 text-sm text-rose-50">
                                <li>• Tentative intent is not a booking.</li>
                                <li>• Venue availability stays unknown until verified.</li>
                                <li>• Policy answers must cite approved sources.</li>
                            </ul>
                        </div>
                    </aside>
                </div>
            </div>
        </div>
    );
}
