import { EventOut } from '@/types/events';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export async function demoLogin(email: string) {
  const res = await fetch(`${API_BASE}/auth/demo-login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  });
  if (!res.ok) throw new Error('Login failed');
  return res.json(); // returns SessionOut
}

export async function getMyEvents(token: string): Promise<EventOut[]> {
  const res = await fetch(`${API_BASE}/events?limit=3`, {
    headers: { 'Authorization': `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Failed to fetch events');
  const data = await res.json();
  return data.items;
}
