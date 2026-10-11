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

  const DEMO_PERSONAS = [
    { label: 'Club Organizer', email: 'organizer@example.invalid', desc: 'Intel IoT & Raagasudha Clubs' },
    { label: 'Campus Admin', email: 'campus-admin@example.invalid', desc: 'Office of Student Affairs (OSA)' },
    { label: 'Club Admin', email: 'club-admin@example.invalid', desc: 'Intel IoT Club Executive' },
    { label: 'Student / Guest', email: 'student@demo.invalid', desc: 'Campus Community Observer' },
  ];

  const handlePersonaSelect = async (targetEmail: string) => {
    await switchPersona(targetEmail);
    setProfile(false);
  };

  const navLinks = links.map(([href, label]) => (
    <Link
      key={href}
      href={href}
      onClick={() => setOpen(false)}
      aria-current={path === href ? 'page' : undefined}
      className={
        'rounded-[10px] px-3 py-1.5 text-sm font-medium transition-all duration-150 active:scale-[0.98] ' +
        (path === href ? 'bg-[#7a1b32]/10 font-semibold text-[#7a1b32]' : 'text-stone-600 hover:bg-stone-200/50 hover:text-stone-900')
      }
    >
      {label}
    </Link>
  ));

  return (
    <header className="fixed inset-x-0 top-0 z-50 h-16 border-b border-stone-200/60 bg-[#F5EEE9]/85 backdrop-blur-xl transition-all print:hidden">
      <div className="flex h-full items-center justify-between gap-3 px-4 lg:px-8">
        <Link href="/" className="shrink-0 font-serif text-xl font-bold tracking-tight text-[#7a1b32] transition-transform active:scale-[0.98]">
          CampusCue
        </Link>
        <nav aria-label="Main navigation" className="hidden items-center gap-1 xl:flex">
          {navLinks}
        </nav>
        <div className="flex items-center gap-2">
          <button
            aria-expanded={profile}
            onClick={() => setProfile(!profile)}
            className="flex items-center gap-2 rounded-[10px] border border-stone-300/80 bg-white/90 px-3.5 py-1.5 text-xs font-semibold text-stone-800 shadow-sm backdrop-blur-md transition-all duration-150 hover:bg-white active:scale-[0.98]"
          >
            <span
              className={
                'inline-block h-2 w-2 rounded-full ' +
                (session
                  ? session.user.campus_admin
                    ? 'bg-purple-600 shadow-[0_0_6px_rgba(147,51,234,0.5)]'
                    : 'bg-emerald-600 shadow-[0_0_6px_rgba(5,150,105,0.5)]'
                  : 'bg-stone-400')
              }
            />
            <span>{isLoading ? 'Loading session…' : session?.user.display_name ?? 'Sign in'}</span>
            {session && (
              <span className="rounded-[6px] bg-stone-100 px-1.5 py-0.5 text-[10px] font-medium text-stone-600">
                {session.user.campus_admin ? 'Admin' : activeClub?.role ?? 'Member'}
              </span>
            )}
          </button>
          <button
            aria-label={open ? 'Close navigation' : 'Open navigation'}
            aria-expanded={open}
            onClick={() => setOpen(!open)}
            className="rounded-[10px] p-2 text-stone-700 transition-all hover:bg-stone-200/50 active:scale-[0.96] xl:hidden"
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>
      {open && (
        <nav aria-label="Mobile navigation" className="flex flex-col gap-1 border-b border-stone-200 bg-[#F5EEE9]/95 p-4 backdrop-blur-xl xl:hidden">
          {navLinks}
        </nav>
      )}
      {profile && (
        <div className="absolute right-3 top-16 w-[min(23rem,calc(100vw-1.5rem))] rounded-[10px] border border-stone-200/80 bg-white/95 p-5 shadow-2xl backdrop-blur-xl transition-all">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold tracking-tight text-stone-900">Demo Persona</h2>
            <button
              onClick={() => setProfile(false)}
              className="rounded-[6px] p-1 text-stone-400 transition hover:bg-stone-100 hover:text-stone-700 active:scale-[0.95]"
              aria-label="Close modal"
            >
              <X size={16} />
            </button>
          </div>
          <p className="my-1.5 text-xs text-stone-600">Select an authoritative demo identity or enter a seeded email.</p>

          <div className="my-3 space-y-1.5">
            {DEMO_PERSONAS.map(p => {
              const active = session?.user.email === p.email;
              return (
                <button
                  key={p.email}
                  type="button"
                  disabled={isLoading}
                  onClick={() => handlePersonaSelect(p.email)}
                  className={
                    'flex w-full flex-col items-start rounded-[10px] border p-2.5 text-left transition-all duration-150 active:scale-[0.98] ' +
                    (active
                      ? 'border-[#7a1b32] bg-rose-50/80 font-medium text-[#7a1b32] shadow-xs'
                      : 'border-stone-200/80 bg-stone-50/60 hover:bg-stone-100/80 text-stone-800')
                  }
                >
                  <div className="flex w-full items-center justify-between text-xs font-semibold">
                    <span>{p.label}</span>
                    {active && <span className="text-[10px] text-[#7a1b32]">Active</span>}
                  </div>
                  <span className="text-[11px] text-stone-500">{p.desc}</span>
                </button>
              );
            })}
          </div>

          {session && (
            <div className="my-3 rounded-[10px] border border-stone-200/60 bg-stone-50/50 p-3 text-xs">
              <p className="font-medium text-stone-900">
                {session.user.email} · {session.user.campus_admin ? 'Campus admin' : activeClub?.role ?? 'Member'}
              </p>
              <label className="mt-2 block text-xs text-stone-700">
                Active club
                <select
                  aria-label="Active club"
                  value={activeClub?.club_id ?? ''}
                  onChange={e => selectClub(e.target.value)}
                  className="mt-1 w-full rounded-[10px] border border-stone-300 bg-white p-2 text-xs transition focus:border-[#7a1b32] focus:outline-none"
                >
                  {(session.user.memberships ?? []).map(c => (
                    <option key={c.club_id} value={c.club_id}>
                      {c.club_name} · {c.role}
                    </option>
                  ))}
                </select>
              </label>
              <button
                onClick={() => {
                  logout();
                  setProfile(false);
                }}
                className="mt-2.5 text-xs font-bold text-[#7a1b32] transition hover:underline active:scale-[0.98]"
              >
                Sign out
              </button>
            </div>
          )}

          <form
            onSubmit={async e => {
              e.preventDefault();
              await handlePersonaSelect(email);
            }}
            className="space-y-2.5 border-t border-stone-100 pt-3"
          >
            <label className="block text-xs font-medium text-stone-700">
              Custom seeded email
              <input
                type="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="mt-1 w-full rounded-[10px] border border-stone-300 bg-white p-2 text-xs transition focus:border-[#7a1b32] focus:outline-none"
              />
            </label>
            <button
              disabled={isLoading}
              className="w-full rounded-[10px] bg-[#7a1b32] p-2 text-xs font-semibold text-white shadow-sm transition-all duration-150 hover:bg-[#631628] active:scale-[0.98] disabled:opacity-50"
            >
              {session ? 'Switch identity' : 'Sign in'}
            </button>
          </form>
          {error && <p role="alert" className="mt-2 text-xs text-rose-800">{error}</p>}
        </div>
      )}
    </header>
  );
}
