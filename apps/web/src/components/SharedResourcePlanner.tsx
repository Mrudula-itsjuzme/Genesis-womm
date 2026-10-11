'use client';

import { useState } from 'react';
import { resourcesApi } from '@/lib/api/endpoints';
import { errorMessage } from '@/lib/api/client';
import { useAuth } from '@/context/AuthContext';
import type { ResourceInterestCreate, ResourceInterestOut } from '@/types/core-api';

type ResourceInterestCategory = ResourceInterestCreate['category'];

const categories: ResourceInterestCategory[] = ['HPC / GPU compute', 'Computer lab', 'AV / recording kit', 'Workshop equipment', 'Other shared resource', 'Er kit', 'Bio signal', 'Eeg kit', 'Hardware sensors and kit', 'Power extensions', 'Wifi support', 'Lab suport', '3d printing', 'Vlsi boards'];

export default function SharedResourcePlanner() {
  const { token } = useAuth();
  const [type, setType] = useState<ResourceInterestCategory>('HPC / GPU compute');
  const [purpose, setPurpose] = useState('');
  const [date, setDate] = useState('');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [requirements, setRequirements] = useState('');
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState<ResourceInterestOut | null>(null);
  const [saving, setSaving] = useState(false);

  const request = [
    'CampusCue · Shared resource interest draft (not a reservation)',
    'Resource: ' + type,
    'Purpose: ' + purpose.trim(),
    'Preferred date: ' + date,
    'Preferred window: ' + start + '–' + end + ' IST',
    requirements.trim() ? 'Requirements: ' + requirements.trim() : '',
    'Availability: UNKNOWN. Confirm access, quotas, eligibility and allocation with the responsible office.',
  ].filter(Boolean).join('\n');

  async function copyRequest() {
    setError('');
    if (!purpose.trim() || !date || !start || !end || end <= start) {
      setError('Add a purpose, date and valid time window before copying a request.');
      return;
    }
    try {
      await navigator.clipboard.writeText(request);
      setCopied(true);
    } catch {
      setError('Clipboard access was blocked. Select and copy the preview below instead.');
    }
  }

  async function saveInterest() {
    setError('');
    if (!purpose.trim() || !date || !start || !end || end <= start) {
      setError('Add a purpose, date and valid time window before saving interest.');
      return;
    }
    if (!token) { setError('Sign in before saving an interest.'); return; }
    setSaving(true);
    try {
      setSaved(await resourcesApi.createInterest(token, { category: type, purpose: purpose.trim(), preferred_date: date, start_time: start, end_time: end, requirements: requirements.trim() || null }));
    } catch (err) {
      setError(errorMessage(err));
    } finally { setSaving(false); }
  }

  function markDraftChanged() {
    setCopied(false);
    setSaved(null);
  }

  const field = 'mt-1 block w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm focus:border-[#7a1b32] focus:outline-none focus:ring-2 focus:ring-[#7a1b32]/15';
  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5" aria-labelledby="shared-resources-heading">
      <div className="mb-4">
        <h2 id="shared-resources-heading" className="text-lg font-bold text-stone-900">Shared resource interest planner</h2>
        <p className="mt-1 text-sm text-stone-600">Coordinate a request for scarce equipment or computing resources, including HPC/GPU access. This small planner produces a draft you can share through your institution’s existing channels. It does not pool accounts, check real availability, allocate compute, or book equipment.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm font-medium">Resource category
          <select className={field} value={type} onChange={e => { setType(e.target.value as ResourceInterestCategory); markDraftChanged(); }}>
            {categories.map(option => <option key={option}>{option}</option>)}
          </select>
        </label>
        <label className="text-sm font-medium">Purpose (no personal or student records)
          <input className={field} maxLength={160} placeholder="e.g. train a workshop demo model" value={purpose} onChange={e => { setPurpose(e.target.value); markDraftChanged(); }} />
        </label>
        <label className="text-sm font-medium">Preferred date
          <input className={field} type="date" value={date} onChange={e => { setDate(e.target.value); markDraftChanged(); }} />
        </label>
        <div className="grid grid-cols-2 gap-2">
          <label className="text-sm font-medium">From (IST)
            <input className={field} type="time" value={start} onChange={e => { setStart(e.target.value); markDraftChanged(); }} />
          </label>
          <label className="text-sm font-medium">Until (IST)
            <input className={field} type="time" value={end} onChange={e => { setEnd(e.target.value); markDraftChanged(); }} />
          </label>
        </div>
        <label className="text-sm font-medium sm:col-span-2">Technical requirements (optional)
          <textarea className={field} rows={2} maxLength={400} value={requirements} onChange={e => { setRequirements(e.target.value); markDraftChanged(); }} placeholder="GPU memory, expected workload, software, required equipment count..." />
        </label>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button type="button" onClick={() => void copyRequest()} className="rounded-lg bg-[#7a1b32] px-4 py-2 text-sm font-semibold text-white hover:bg-[#631628]">Copy request draft</button>
        <button type="button" disabled={saving || !token} onClick={() => void saveInterest()} className="rounded-lg border border-[#7a1b32] px-4 py-2 text-sm font-semibold text-[#7a1b32] disabled:opacity-50">{saving ? 'Saving…' : 'Save interest'}</button>
        {copied && <p role="status" className="text-sm text-emerald-700">Copied. Share only with the appropriate resource owner.</p>}
        {saved && <p role="status" className="text-sm text-emerald-700">Interest saved for {saved.category}. This is not a booking or allocation.</p>}
      </div>
      {error && <p role="alert" className="mt-2 text-sm text-rose-800">{error}</p>}
      <details className="mt-4 rounded-lg bg-stone-50 p-3 text-sm">
        <summary className="cursor-pointer font-medium">Preview draft</summary>
        <pre className="mt-2 whitespace-pre-wrap break-words font-sans text-xs text-stone-700">{request}</pre>
      </details>
      <p className="mt-3 text-xs text-stone-500">Privacy: do not include passwords, account IDs, private faculty details, student records, personal contact information or confidential research datasets. Nothing is sent to CampusCue’s RAG index by this planner.</p>
    </section>
  );
}
