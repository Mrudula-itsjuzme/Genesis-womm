'use client';
import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import type { ReactNode } from 'react';
import type { SessionOut, MembershipOut } from '@/types/core-api';
import { authApi } from '@/lib/api/endpoints';
import { errorMessage } from '@/lib/api/client';
import { SESSION_KEY, restoreSession } from '@/lib/session';

type Auth = { session: SessionOut | null; token: string | null; activeClub: MembershipOut | null; isLoading: boolean; error: string | null; switchPersona: (email: string) => Promise<void>; logout: () => void; selectClub: (id: string) => void };
const AuthContext = createContext<Auth | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionOut | null>(null);
  const [clubId, setClubId] = useState('');
  const [isLoading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const generation = useRef(0);
  const logout = useCallback(() => { generation.current++; setSession(null); setClubId(''); setLoading(false); try { localStorage.removeItem(SESSION_KEY); } catch { /* Storage may be disabled. */ } }, []);
  const switchPersona = useCallback(async (email: string) => {
    logout(); const turn = ++generation.current; setLoading(true); setError(null);
    try {
      const result = await authApi.demoLogin(email.trim());
      if (turn !== generation.current) return;
      setSession(result);
      try { localStorage.setItem(SESSION_KEY, JSON.stringify(result)); } catch { /* The session still works without persistence. */ }
    } catch (err) { if (turn === generation.current) setError(errorMessage(err)); }
    finally { if (turn === generation.current) setLoading(false); }
  }, [logout]);
  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => {
      if (!active) return;
      try { const restored = restoreSession(localStorage.getItem(SESSION_KEY)); setSession(restored); if (!restored) localStorage.removeItem(SESSION_KEY); } catch { setSession(null); }
      setLoading(false);
    });
    const synchronize = () => { logout(); };
    window.addEventListener('storage', synchronize);
    return () => { active = false; window.removeEventListener('storage', synchronize); };
  }, [logout]);
  useEffect(() => {
    const expired = (event: Event) => { if ((event as CustomEvent).detail === session?.access_token) logout(); };
    window.addEventListener('campuscue:unauthenticated', expired);
    let timer: ReturnType<typeof setTimeout> | null = null;
    function scheduleExpiry() {
      if (!session) return;
      const remaining = Date.parse(session.expires_at) - Date.now();
      if (remaining <= 0) { logout(); return; }
      timer = setTimeout(scheduleExpiry, Math.min(remaining, 2_147_483_647));
    }
    scheduleExpiry();
    return () => { window.removeEventListener('campuscue:unauthenticated', expired); if (timer !== null) clearTimeout(timer); };
  }, [session, logout]);
  const clubs = session?.user.memberships ?? [];
  const activeClub = clubs.find(c => c.club_id === clubId) ?? clubs[0] ?? null;
  return <AuthContext.Provider value={{ session, token: session?.access_token ?? null, activeClub, isLoading, error, switchPersona, logout, selectClub: setClubId }}>{children}</AuthContext.Provider>;
}
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error('AuthProvider is required.'); return value; }
