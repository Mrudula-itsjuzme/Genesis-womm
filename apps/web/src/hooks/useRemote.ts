'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { errorMessage } from '@/lib/api/client';

/** A changed identity/query hides old data immediately; aborted responses cannot replace it. */
export function useRemote<T>(key: string | null, loader: (signal: AbortSignal) => Promise<T>) {
  const latest = useRef(loader);
  useEffect(() => { latest.current = loader; });
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<{ key: string | null; attempt: number; data?: T; error?: string; loading: boolean }>({ key: null, attempt: 0, loading: false });
  useEffect(() => {
    if (!key) return;
    const controller = new AbortController();
    Promise.resolve().then(async () => {
      if (controller.signal.aborted) return;
      setState({ key, attempt, loading: true });
      try {
        const data = await latest.current(controller.signal);
        if (!controller.signal.aborted) setState({ key, attempt, data, loading: false });
      } catch (error) {
        if (!controller.signal.aborted) setState({ key, attempt, error: errorMessage(error), loading: false });
      }
    });
    return () => controller.abort();
  }, [key, attempt]);
  const current = state.key === key && state.attempt === attempt;
  const retry = useCallback(() => setAttempt(n => n + 1), []);
  return { data: key && current ? state.data : undefined, error: key && current ? state.error : undefined, loading: Boolean(key && (!current || state.loading)), retry };
}
