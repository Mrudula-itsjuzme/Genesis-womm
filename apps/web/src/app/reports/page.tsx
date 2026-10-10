'use client';

import { useState } from 'react';
import { FileText, Download, Save, Sparkles, AlertTriangle, CheckCircle2, PencilLine } from 'lucide-react';

const reportDraft = `INIT AI Hackathon — Draft report

Summary:
- Event is currently tentative and listed under the AI Club planning pipeline.
- Preferred venue remains Acharya Hall, but formal confirmation has not yet been received.
- Major dependencies include faculty sponsorship, ICTS support, and event security coordination.

Open items:
- Facilities confirmation for hall assignment
- Final sponsor approval
- Security coordination for guest attendance
- Event registration flows and student announcement timing

Recommendation:
The event should stay in proposal mode until venue approval and sponsor details are verified.`;

const requiredFields = [
    'Event title',
    'Venue status',
    'Faculty sponsor',
    'Security needs',
    'Student registration mode',
];

export default function ReportsPage() {
    const [draft, setDraft] = useState(reportDraft);

    return (
        <div className="min-h-screen bg-[#F5EEE9] px-6 py-8 lg:px-10">
            <div className="mx-auto max-w-7xl space-y-8">
                <header className="flex flex-col gap-4 rounded-[28px] bg-white p-6 shadow-[0_8px_25px_rgba(122,27,50,0.06)] ring-1 ring-[#f0e1dc] lg:flex-row lg:items-center lg:justify-between">
                    <div>
                        <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#7a1b32]">Draft reports</p>
                        <h1 className="mt-2 text-3xl font-bold tracking-tight text-gray-900">Event Report Studio</h1>
                    </div>
                    <div className="flex gap-3">
                        <button className="inline-flex items-center gap-2 rounded-full border border-[#f0dfe4] bg-[#fffaf8] px-4 py-2 text-sm font-semibold text-[#7a1b32]">
                            <Save className="h-4 w-4" />
                            Save draft
                        </button>
                        <button className="inline-flex items-center gap-2 rounded-full bg-[#7a1b32] px-4 py-2 text-sm font-semibold text-white shadow-md shadow-[#7a1b32]/20">
                            <Download className="h-4 w-4" />
                            Export
                        </button>
                    </div>
                </header>

                <div className="grid gap-8 lg:grid-cols-[0.9fr_1.1fr]">
                    <aside className="space-y-6">
                        <div className="rounded-[28px] bg-white p-5 shadow-[0_8px_25px_rgba(122,27,50,0.06)] ring-1 ring-[#f0e1dc]">
                            <div className="flex items-center gap-2 text-[#7a1b32]">
                                <Sparkles className="h-4 w-4" />
                                <p className="text-xs font-bold uppercase tracking-[0.18em]">Checklist</p>
                            </div>

                            <div className="mt-5 space-y-3">
                                {requiredFields.map((field) => (
                                    <div key={field} className="flex items-center justify-between rounded-2xl border border-[#f0e1dc] bg-[#fffaf8] px-3 py-2.5">
                                        <span className="text-sm font-medium text-gray-700">{field}</span>
                                        <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-amber-700">
                                            <AlertTriangle className="h-3 w-3" />
                                            Missing
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="rounded-[28px] bg-[#fffaf8] p-5 shadow-[0_8px_25px_rgba(122,27,50,0.06)] ring-1 ring-[#f0e1dc]">
                            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#7a1b32]">Status</p>
                            <div className="mt-4 space-y-3">
                                <div className="flex items-center justify-between rounded-2xl bg-white px-3 py-2">
                                    <span className="text-sm text-gray-700">Venue confirmed</span>
                                    <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-rose-700">
                                        <AlertTriangle className="h-3 w-3" />
                                        No
                                    </span>
                                </div>
                                <div className="flex items-center justify-between rounded-2xl bg-white px-3 py-2">
                                    <span className="text-sm text-gray-700">Policy citation complete</span>
                                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-emerald-700">
                                        <CheckCircle2 className="h-3 w-3" />
                                        Yes
                                    </span>
                                </div>
                            </div>
                        </div>
                    </aside>

                    <section className="rounded-[28px] bg-white p-5 shadow-[0_8px_25px_rgba(122,27,50,0.06)] ring-1 ring-[#f0e1dc]">
                        <div className="flex items-center justify-between gap-3 border-b border-[#f0e1dc] pb-4">
                            <div className="flex items-center gap-3">
                                <div className="rounded-xl bg-[#fff5f0] p-2.5 text-[#7a1b32]">
                                    <FileText className="h-5 w-5" />
                                </div>
                                <div>
                                    <h2 className="text-lg font-bold text-gray-900">Report draft</h2>
                                    <p className="text-xs uppercase tracking-[0.16em] text-gray-500">INIT AI Hackathon</p>
                                </div>
                            </div>
                            <div className="inline-flex items-center gap-2 rounded-full bg-[#fff5f0] px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.14em] text-[#7a1b32]">
                                <PencilLine className="h-3.5 w-3.5" />
                                Editable
                            </div>
                        </div>

                        <textarea
                            value={draft}
                            onChange={(event) => setDraft(event.target.value)}
                            className="mt-5 h-[420px] w-full resize-none rounded-[22px] border border-[#f0e1dc] bg-[#fffdfc] p-4 text-sm leading-7 text-gray-700 outline-none ring-0 transition focus:border-[#e7b8c3]"
                        />
                    </section>
                </div>
            </div>
        </div>
    );
}
