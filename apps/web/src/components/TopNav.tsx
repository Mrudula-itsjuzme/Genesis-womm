'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { Menu, X } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
const links = [['/', 'Home'], ['/plan', 'Plan Event'], ['/calendar', 'Calendar'], ['/venues', 'Venues'], ['/policy', 'Ask CampusCue'], ['/changes', 'Changes'], ['/reports', 'Reports'], ['/resources', 'Resources']];
export default function TopNav() {
  const path = usePathname();
  const { session, activeClub, selectClub, switchPersona, logout, isLoading, error } = useAuth();
  const [open, setOpen] = useState(false);
  const [profile, setProfile] = useState(false);
  const [email, setEmail] = useState('organizer@example.invalid');
  const navLinks = links.map(([href, label]) => <Link key={href} href={href} onClick={() => setOpen(false)} aria-current={path === href ? 'page' : undefined} className={'px-3 py-2 text-sm font-semibold ' + (path === href ? 'text-[#7a1b32] underline underline-offset-8' : 'text-gray-600')}>{label}</Link>);
  return <header className="fixed inset-x-0 top-0 z-50 h-16 border-b border-rose-100 bg-[#F5EEE9]/95 backdrop-blur-md print:hidden">
    <div className="flex h-full items-center justify-between gap-3 px-4 lg:px-8">
      <Link href="/" className="shrink-0 font-serif text-xl font-bold text-[#7a1b32]">CampusCue</Link>
      <nav aria-label="Main navigation" className="hidden xl:flex">{navLinks}</nav>
      <div className="flex gap-2">
        <button aria-expanded={profile} onClick={() => setProfile(!profile)} className="rounded-xl border border-stone-300 bg-white px-3 py-2 text-xs font-semibold">{isLoading ? 'Loading session…' : session?.user.display_name ?? 'Sign in'}</button>
        <button aria-label={open ? 'Close navigation' : 'Open navigation'} aria-expanded={open} onClick={() => setOpen(!open)} className="p-2 xl:hidden">{open ? <X size={20} /> : <Menu size={20} />}</button>
      </div>
    </div>
    {open && <nav aria-label="Mobile navigation" className="flex flex-col border-b bg-[#F5EEE9] p-4 xl:hidden">{navLinks}</nav>}
    {profile && <div className="absolute right-3 top-16 w-[min(22rem,calc(100vw-1.5rem))] rounded-2xl border border-stone-200 bg-white p-5 shadow-xl">
      <h2 className="font-semibold">Demo identity</h2><p className="my-2 text-xs text-gray-600">Sign in with a seeded demo email. Roles are assigned by Core.</p>
      {session && <><p className="text-xs">{session.user.email} · {session.user.campus_admin ? 'Campus admin' : activeClub?.role ?? 'Member'}{session.user.synthetic ? ' · Synthetic demo' : ''}</p>
        <label className="mt-3 block text-xs">Active club<select aria-label="Active club" value={activeClub?.club_id ?? ''} onChange={e => selectClub(e.target.value)} className="mt-1 w-full rounded-lg border p-2">{(session.user.memberships ?? []).map(c => <option key={c.club_id} value={c.club_id}>{c.club_name} · {c.role}</option>)}</select></label>
        <button onClick={logout} className="my-3 text-xs font-bold text-[#7a1b32]">Sign out</button></>}
      <form onSubmit={e => { e.preventDefault(); void switchPersona(email); }} className="space-y-3">
        <label className="block text-xs">Seeded email<input type="email" required value={email} onChange={e => setEmail(e.target.value)} className="mt-1 w-full rounded-lg border p-2" /></label>
        <button disabled={isLoading} className="w-full rounded-lg bg-[#7a1b32] p-2 text-sm text-white disabled:opacity-50">{session ? 'Switch identity' : 'Sign in'}</button>
      </form>{error && <p role="alert" className="mt-3 text-xs text-rose-800">{error}</p>}
    </div>}
  </header>;
}
