'use client';
import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
type Toast = { id: string; type: 'success' | 'error' | 'info'; title: string; message?: string };
const Context = createContext<(type: Toast['type'], title: string, message?: string) => void>(() => {});
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const toast = useCallback((type: Toast['type'], title: string, message?: string) => {
    const id = crypto.randomUUID(); setItems(previous => [...previous, { id, type, title, message }]);
    timers.current.push(setTimeout(() => setItems(previous => previous.filter(t => t.id !== id)), 6000));
  }, []);
  useEffect(() => () => timers.current.forEach(clearTimeout), []);
  return <Context.Provider value={toast}>{children}<div aria-live="polite" className="fixed bottom-4 right-4 z-[70] w-[min(24rem,calc(100vw-2rem))] space-y-2">{items.map(t => <div key={t.id} role={t.type === 'error' ? 'alert' : 'status'} className={'rounded-xl border p-4 shadow-lg ' + (t.type === 'error' ? 'border-rose-300 bg-rose-50' : t.type === 'success' ? 'border-emerald-300 bg-emerald-50' : 'bg-white')}><button aria-label="Dismiss notification" onClick={() => setItems(previous => previous.filter(item => item.id !== t.id))} className="float-right ml-2">×</button><p className="text-sm font-bold">{t.title}</p><p className="mt-1 text-xs">{t.message}</p></div>)}</div></Context.Provider>;
}
export function useToast() { return { toast: useContext(Context) }; }
