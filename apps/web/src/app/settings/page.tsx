'use client';
import { useAuth } from '@/context/AuthContext';
export default function SettingsPage() {
  const { session, activeClub, logout } = useAuth();
  return <section className="mx-auto max-w-3xl p-4 md:p-8"><h1 className="text-3xl font-bold text-[#7a1b32]">Account settings</h1><div className="my-5 space-y-3 rounded-2xl border bg-white p-5">
    {session ? <><p>{session.user.display_name} · {session.user.email}</p><p>{session.user.campus_admin ? 'Campus admin' : activeClub?.role ?? 'Member'} · {activeClub?.club_name ?? 'No active club'}</p><p>{session.user.synthetic ? 'Demo identity' : 'Core directory identity'}</p><button className="rounded border p-3" onClick={logout}>Sign out</button></> : <p>Use the profile menu to sign in.</p>}
    <p className="text-sm">Notification delivery and shared account preferences are not available yet. Report drafts are stored locally in your browser.</p>
  </div></section>;
}
