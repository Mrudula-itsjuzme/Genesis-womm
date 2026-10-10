'use client';

import { useState } from 'react';
import { Bell, Database, ShieldCheck, SlidersHorizontal, UserRound } from 'lucide-react';

const toggles = [
    { label: 'Weekly digest email', value: true },
    { label: 'Conflict reminders', value: true },
    { label: 'Policy citation summaries', value: false },
    { label: 'Student registration alerts', value: true },
];

export default function SettingsPage() {
    const [prefs, setPrefs] = useState(toggles);

    const updateToggle = (index: number) => {
        setPrefs((current) =>
            current.map((item, itemIndex) =>
                itemIndex === index ? { ...item, value: !item.value } : item,
            ),
        );
    };

    return (
        <div className="min-h-screen bg-[#F5EEE9] px-6 py-8 lg:px-10">
            <div className="mx-auto max-w-6xl space-y-8">
                <header className="rounded-[28px] bg-white p-6 shadow-[0_8px_25px_rgba(122,27,50,0.06)] ring-1 ring-[#f0e1dc]">
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#7a1b32]">Account</p>
                    <h1 className="mt-2 text-3xl font-bold tracking-tight text-gray-900">Settings</h1>
                </header>

                <div className="grid gap-8 lg:grid-cols-[0.95fr_1.05fr]">
                    <aside className="space-y-6">
                        <div className="rounded-[28px] bg-white p-5 shadow-[0_8px_25px_rgba(122,27,50,0.06)] ring-1 ring-[#f0e1dc]">
                            <div className="flex items-center gap-3">
                                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#fff5f0] text-[#7a1b32]">
                                    <UserRound className="h-5 w-5" />
                                </div>
                                <div>
                                    <h2 className="text-lg font-bold text-gray-900">Arjun Admin</h2>
                                    <p className="text-sm text-gray-500">Club Admin · AI Club</p>
                                </div>
                            </div>

                            <div className="mt-5 rounded-2xl bg-[#fffaf8] p-4 text-sm text-gray-700 ring-1 ring-[#f0e1dc]">
                                <p className="font-semibold text-gray-900">Role access</p>
                                <p className="mt-2">Can view internal committee workflows, approve event drafts, and manage venue requests.</p>
                            </div>
                        </div>

                        <div className="rounded-[28px] bg-[#7a1b32] p-5 text-white shadow-[0_8px_25px_rgba(122,27,50,0.24)]">
                            <div className="flex items-center gap-2 text-rose-100">
                                <ShieldCheck className="h-4 w-4" />
                                <span className="text-xs font-bold uppercase tracking-[0.16em]">Security</span>
                            </div>
                            <p className="mt-3 text-sm leading-7 text-rose-50">
                                CampusCue keeps source-backed policy and operational state separate from AI drafting behavior.
                            </p>
                        </div>
                    </aside>

                    <section className="space-y-6">
                        <div className="rounded-[28px] bg-white p-5 shadow-[0_8px_25px_rgba(122,27,50,0.06)] ring-1 ring-[#f0e1dc]">
                            <div className="flex items-center gap-2 text-[#7a1b32]">
                                <Bell className="h-4 w-4" />
                                <p className="text-xs font-bold uppercase tracking-[0.18em]">Notifications</p>
                            </div>

                            <div className="mt-5 space-y-3">
                                {prefs.map((item, index) => (
                                    <div key={item.label} className="flex items-center justify-between rounded-2xl border border-[#f0e1dc] bg-[#fffaf8] px-3 py-3">
                                        <span className="text-sm font-medium text-gray-700">{item.label}</span>
                                        <button
                                            type="button"
                                            onClick={() => updateToggle(index)}
                                            className={`relative h-7 w-12 rounded-full transition ${item.value ? 'bg-[#7a1b32]' : 'bg-[#e8d9d6]'}`}
                                            aria-label={item.label}
                                        >
                                            <span
                                                className={`absolute top-1 h-5 w-5 rounded-full bg-white shadow-sm transition ${item.value ? 'left-6' : 'left-1'}`}
                                            />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="rounded-[28px] bg-white p-5 shadow-[0_8px_25px_rgba(122,27,50,0.06)] ring-1 ring-[#f0e1dc]">
                            <div className="flex items-center gap-2 text-[#7a1b32]">
                                <SlidersHorizontal className="h-4 w-4" />
                                <p className="text-xs font-bold uppercase tracking-[0.18em]">Preferences</p>
                            </div>

                            <div className="mt-5 space-y-4">
                                <div className="rounded-2xl border border-[#f0e1dc] bg-[#fffaf8] p-4">
                                    <div className="flex items-center gap-3">
                                        <Database className="h-4 w-4 text-[#7a1b32]" />
                                        <span className="text-sm font-semibold text-gray-800">Source preferences</span>
                                    </div>
                                    <p className="mt-2 text-sm text-gray-600">Policy answers use the OSA Handbook and verified campus sources before presenting any recommendation.</p>
                                </div>

                                <div className="rounded-2xl border border-[#f0e1dc] bg-[#fffaf8] p-4">
                                    <div className="flex items-center gap-3">
                                        <ShieldCheck className="h-4 w-4 text-[#7a1b32]" />
                                        <span className="text-sm font-semibold text-gray-800">Data privacy</span>
                                    </div>
                                    <p className="mt-2 text-sm text-gray-600">CampusCue does not infer official approval from tentative or requested status entries.</p>
                                </div>
                            </div>
                        </div>
                    </section>
                </div>
            </div>
        </div>
    );
}
