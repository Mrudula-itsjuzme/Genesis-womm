'use client';
import { useState, useRef } from 'react';
import type { FormEvent } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { useRemote } from '@/hooks/useRemote';
import { eventsApi, resourcesApi, proposalsApi } from '@/lib/api/endpoints';
import { errorMessage } from '@/lib/api/client';
import { toCampusISO, validateEventPlan } from '@/lib/campus-time';
import type { EventCreate, EventCreatedOut } from '@/types/core-api';
import ConflictSidebar from '@/components/ConflictSidebar';
import RemoteState from '@/components/RemoteState';
import { useToast } from '@/components/Toast';
import ProposalUpload from '@/components/ProposalUpload';

const inputStyle = 'mt-1 block w-full rounded-[10px] border border-stone-300/80 bg-white p-2.5 text-sm transition-all focus:border-[#7a1b32] focus:outline-none focus:ring-2 focus:ring-[#7a1b32]/15';
const sectionHeaderStyle = 'flex items-center gap-2 border-b border-stone-200 pb-2 text-base font-bold text-stone-900';

export default function PlanPage() {
  const { token, activeClub } = useAuth();
  return <PlanFacilityBookingForm key={token + ':' + activeClub?.club_id} />;
}

function PlanFacilityBookingForm() {
  const { token, activeClub } = useAuth();
  const { toast } = useToast();

  // 1. Name of Event & Description
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');

  // 2. Dept / Club organizing
  const deptOrganizing = activeClub?.club_name ?? 'Club / Department Organizing';

  // 3. Date(s) & Time
  const [date, setDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');

  // 4. Organizing Secretary / Faculty / Staff Responsible
  const [organizerContact, setOrganizerContact] = useState('');

  // 5. Participants breakdown
  const [nationalMale, setNationalMale] = useState('');
  const [nationalFemale, setNationalFemale] = useState('');
  const [intlMale, setIntlMale] = useState('');
  const [intlFemale, setIntlFemale] = useState('');

  // 6. Academic approval copy (PDF)
  const [approvalFile, setApprovalFile] = useState<File | null>(null);

  // 7. Hall(s) required (primary venue + additional halls)
  const [venue, setVenue] = useState('');
  const [additionalHalls, setAdditionalHalls] = useState<string[]>([]);

  // 8. Other campus infrastructure
  const [otherInfrastructure, setOtherInfrastructure] = useState('');

  // 9. AV Requirements
  const [avRequirements, setAvRequirements] = useState('');

  // 10. Food & Refreshments Table
  const [foodRows, setFoodRows] = useState<Array<{ date: string; breakfast: boolean; tea11am: boolean; tea3pm: boolean; lunch: boolean; dinner: boolean; count: string }>>([
    { date: '', breakfast: false, tea11am: false, tea3pm: false, lunch: false, dinner: false, count: '' }
  ]);

  // 11. Vehicle Requirements
  const [vehicleRows, setVehicleRows] = useState<Array<{ date: string; vehicleType: string }>>([
    { date: '', vehicleType: '' }
  ]);

  // 12. Guest & Hostel Rooms
  const [guestHouseAc, setGuestHouseAc] = useState('');
  const [annexeAc, setAnnexeAc] = useState('');
  const [hostelBoys, setHostelBoys] = useState('');
  const [hostelGirls, setHostelGirls] = useState('');

  // 13. Publicity & Media
  const [flexMainGate, setFlexMainGate] = useState(false);
  const [flexVenue, setFlexVenue] = useState(false);
  const [flexDigitalBackdrop, setFlexDigitalBackdrop] = useState(false);
  const [photographyAoc, setPhotographyAoc] = useState<'YES' | 'NO'>('NO');
  const [mediaCoverageAoc, setMediaCoverageAoc] = useState<'YES' | 'NO'>('NO');

  // 14. Funding of Event
  const [fundingSource, setFundingSource] = useState('By University');

  // 15. Additional Requirements
  const [additionalNotes, setAdditionalNotes] = useState('');

  // Submission State
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [created, setCreated] = useState<EventCreatedOut | null>(null);
  const pending = useRef<{ payload: string; key: string } | null>(null);

  const venues = useRemote(token, signal => resourcesApi.list(token!, { kind: 'VENUE', limit: 100 }, signal));

  // Compute total expected attendance from participant breakdown
  const natM = parseInt(nationalMale || '0', 10);
  const natF = parseInt(nationalFemale || '0', 10);
  const intlM = parseInt(intlMale || '0', 10);
  const intlF = parseInt(intlFemale || '0', 10);
  const totalParticipants = natM + natF + intlM + intlF;

  // Build candidate event object for core-api
  let candidate: EventCreate | null = null;
  let validation = '';
  try {
    if (activeClub && date && start && end && title) {
      // Assemble full structured description preserving all AMRITA Facility Booking items
      const fullDescription = [
        description.trim(),
        organizerContact ? `\n[Organizing Secretary/Faculty Contact]: ${organizerContact.trim()}` : '',
        totalParticipants > 0 ? `\n[Participants Breakdown]: Total: ${totalParticipants} (National: M ${natM}, F ${natF}; International: M ${intlM}, F ${intlF})` : '',
        additionalHalls.length > 0 ? `\n[Additional Halls]: ${additionalHalls.join(', ')}` : '',
        otherInfrastructure.trim() ? `\n[Other Infrastructure]: ${otherInfrastructure.trim()}` : '',
        avRequirements.trim() ? `\n[Audio/Video Requirements]: ${avRequirements.trim()}` : '',
        foodRows.some(r => r.date || r.count) ? `\n[Food/Refreshments]: ${JSON.stringify(foodRows.filter(r => r.date || r.count))}` : '',
        vehicleRows.some(r => r.date || r.vehicleType) ? `\n[Vehicle Requirements]: ${JSON.stringify(vehicleRows.filter(r => r.date || r.vehicleType))}` : '',
        (guestHouseAc || annexeAc || hostelBoys || hostelGirls) ? `\n[Rooms Required]: Guest House: ${guestHouseAc || 0}, Annexe: ${annexeAc || 0}, Boys Hostel: ${hostelBoys || 0}, Girls Hostel: ${hostelGirls || 0}` : '',
        `\n[Publicity]: Flex Main Gate: ${flexMainGate ? 'YES' : 'NO'}, Flex Venue: ${flexVenue ? 'YES' : 'NO'}, Digital Backdrop: ${flexDigitalBackdrop ? 'YES' : 'NO'}, Photography AOC: ${photographyAoc}, Media Coverage AOC: ${mediaCoverageAoc}`,
        `\n[Funding]: ${fundingSource}`,
        additionalNotes.trim() ? `\n[Additional Notes]: ${additionalNotes.trim()}` : ''
      ].filter(Boolean).join('\n');

      candidate = {
        club_id: activeClub.club_id,
        title: title.trim(),
        description: fullDescription || null,
        start_at: toCampusISO(date, start),
        end_at: toCampusISO(endDate || date, end),
        resource_id: venue || null,
        expected_attendance: totalParticipants > 0 ? totalParticipants : null,
        audience_tags: []
      };
      validation = validateEventPlan(candidate) || '';
    }
  } catch (err) {
    validation = errorMessage(err);
  }

  const payload = candidate && !validation ? JSON.stringify(candidate) : null;
  const preview = useRemote(token && payload && !created ? token + payload : null, async signal => {
    await new Promise<void>((resolve, reject) => {
      const timer = setTimeout(resolve, 450);
      signal.addEventListener('abort', () => {
        clearTimeout(timer);
        reject(new DOMException('Aborted', 'AbortError'));
      }, { once: true });
    });
    return eventsApi.preview(token!, JSON.parse(payload!), signal);
  });

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!token || !candidate || validation || saving || created || !activeClub) return;
    const body = JSON.stringify(candidate);
    if (pending.current?.payload !== body) pending.current = { payload: body, key: crypto.randomUUID() };
    setSaving(true);
    setError('');
    try {
      const result = await eventsApi.create(token, candidate, pending.current.key);
      setCreated(result);

      // If user attached academic approval PDF, automatically upload proposal to the created event
      if (approvalFile) {
        try {
          await proposalsApi.upload(token, activeClub.club_id, result.event.id, approvalFile, `Dean Academic Approval - ${title.trim()}`);
          toast('success', 'Event & Approval Submitted', 'Saved event draft and uploaded Dean Academic Approval copy.');
        } catch (uploadErr) {
          toast('info', 'Draft Saved', `Event saved, but proposal upload note: ${errorMessage(uploadErr)}`);
        }
      } else {
        toast('success', 'Event draft saved', 'A draft proposal is not a confirmed booking.');
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="mx-auto max-w-6xl p-4 md:p-8">
      {/* Official Amrita Vishwa Vidyapeetham Header Banner */}
      <div className="mb-6 rounded-2xl border border-stone-200/90 bg-white p-6 shadow-sm">
        <div className="flex flex-col items-center text-center sm:flex-row sm:items-start sm:text-left gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-xl bg-[#7a1b32] font-serif text-2xl font-bold text-white shadow-xs">
            AVV
          </div>
          <div className="flex-1">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-semibold tracking-wider uppercase text-stone-500">Page | 24–26 · Form Rev. 15-Nov-24</span>
              <span className="rounded-full bg-[#7a1b32]/10 px-2.5 py-0.5 text-xs font-semibold text-[#7a1b32]">Amrita Coimbatore Campus</span>
            </div>
            <h1 className="mt-1 text-2xl sm:text-3xl font-extrabold tracking-tight text-stone-900">
              AMRITA VISHWA VIDYAPEETHAM
            </h1>
            <p className="text-sm font-semibold text-stone-700">Coimbatore Campus · Events Department</p>
            <p className="mt-1 text-sm font-medium text-[#7a1b32]">
              Revised Form : Facility booking for events - Coimbatore campus (To be submitted to Events Dept)
            </p>
          </div>
        </div>
      </div>

      {!token ? (
        <RemoteState signedIn={false} loading={false} retry={() => {}} />
      ) : !activeClub ? (
        <div className="rounded-[10px] border border-amber-200/80 bg-amber-50/90 p-6 text-amber-900 shadow-sm backdrop-blur-md">
          <div className="flex items-center gap-2 font-semibold">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-purple-600 shadow-[0_0_6px_rgba(147,51,234,0.5)]"></span>
            <span>Campus Administrator Mode</span>
          </div>
          <p className="mt-2 text-sm text-amber-800">
            Administrative accounts do not hold direct club memberships. To review submitted drafts, resolve conflicts, and grant official confirmations, visit the review workspace.
          </p>
          <Link
            href="/changes"
            className="mt-4 inline-block rounded-[10px] bg-[#7a1b32] px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-all duration-150 ease-out hover:bg-[#631628] active:scale-[0.98]"
          >
            Go to Event Approvals & Changes →
          </Link>
        </div>
      ) : (
        <>
          <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
            <form onSubmit={submit} className="space-y-6 rounded-2xl border border-stone-200/90 bg-white/95 p-6 shadow-sm backdrop-blur-xl">
              <fieldset disabled={saving || Boolean(created)} className="space-y-6">
                
                {/* 1. Name of the Event */}
                <div className="space-y-1">
                  <label className="block text-sm font-semibold text-stone-800">
                    1. Name of the Event <span className="text-rose-600">*</span>
                  </label>
                  <input
                    required
                    maxLength={200}
                    placeholder="e.g. Anokha Tech Fest 2026 - Hackathon Track"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    className={inputStyle}
                  />
                </div>

                {/* 2. Dept organizing the Event */}
                <div className="space-y-1">
                  <label className="block text-sm font-semibold text-stone-800">
                    2. Dept / Club organizing the Event
                  </label>
                  <input
                    readOnly
                    value={deptOrganizing}
                    className="mt-1 block w-full rounded-[10px] border border-stone-200 bg-stone-100/80 p-2.5 text-sm font-medium text-stone-700 cursor-not-allowed"
                  />
                  <p className="text-xs text-stone-500">Automatically associated with your active club session.</p>
                </div>

                {/* 3. Date(s) of Event & Timings */}
                <div className="space-y-2">
                  <label className="block text-sm font-semibold text-stone-800">
                    3. Date(s) & Timings of Event <span className="text-rose-600">*</span>
                  </label>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <label className="text-xs font-medium text-stone-600">
                      Start Date
                      <input type="date" required value={date} onChange={e => setDate(e.target.value)} className={inputStyle} />
                    </label>
                    <label className="text-xs font-medium text-stone-600">
                      Start Time (Asia/Kolkata)
                      <input type="time" required value={start} onChange={e => setStart(e.target.value)} className={inputStyle} />
                    </label>
                    <label className="text-xs font-medium text-stone-600">
                      End Date
                      <input type="date" value={endDate || date} onChange={e => setEndDate(e.target.value)} className={inputStyle} />
                    </label>
                    <label className="text-xs font-medium text-stone-600">
                      End Time (Asia/Kolkata)
                      <input type="time" required value={end} onChange={e => setEnd(e.target.value)} className={inputStyle} />
                    </label>
                  </div>
                </div>

                {/* 4. Organizing secretary/Faculty/Staff responsible */}
                <div className="space-y-1">
                  <label className="block text-sm font-semibold text-stone-800">
                    4. Name & Mob no of Organizing secretary / Faculty / Staff responsible <span className="text-rose-600">*</span>
                  </label>
                  <input
                    required
                    placeholder="e.g. Dr. S. Mahadevan (+91 94440 12345)"
                    value={organizerContact}
                    onChange={e => setOrganizerContact(e.target.value)}
                    className={inputStyle}
                  />
                </div>

                {/* 5. Approximate number of Participants */}
                <div className="space-y-2 rounded-xl border border-stone-200 bg-stone-50/60 p-4">
                  <div className="flex items-center justify-between">
                    <label className="block text-sm font-semibold text-stone-800">
                      5. Approximate number of Participants
                    </label>
                    <span className="rounded-md bg-stone-200 px-2.5 py-0.5 text-xs font-bold text-stone-800">
                      Calculated Total: {totalParticipants}
                    </span>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-1">
                      <span className="text-xs font-semibold text-stone-700">(i) National</span>
                      <div className="grid grid-cols-2 gap-2">
                        <input
                          type="number"
                          min="0"
                          placeholder="Male"
                          value={nationalMale}
                          onChange={e => setNationalMale(e.target.value)}
                          className={inputStyle}
                        />
                        <input
                          type="number"
                          min="0"
                          placeholder="Female"
                          value={nationalFemale}
                          onChange={e => setNationalFemale(e.target.value)}
                          className={inputStyle}
                        />
                      </div>
                    </div>
                    <div className="space-y-1">
                      <span className="text-xs font-semibold text-stone-700">(ii) International</span>
                      <div className="grid grid-cols-2 gap-2">
                        <input
                          type="number"
                          min="0"
                          placeholder="Male"
                          value={intlMale}
                          onChange={e => setIntlMale(e.target.value)}
                          className={inputStyle}
                        />
                        <input
                          type="number"
                          min="0"
                          placeholder="Female"
                          value={intlFemale}
                          onChange={e => setIntlFemale(e.target.value)}
                          className={inputStyle}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* 6. Academic Approval copy from Dean of School */}
                <div className="space-y-1 rounded-xl border border-stone-200 bg-stone-50/60 p-4">
                  <label className="block text-sm font-semibold text-stone-800">
                    6. Academic Approval copy from Dean of School
                  </label>
                  <p className="text-xs text-stone-600">
                    Please enclose photocopy / digital PDF of Academic approval of Dean with respect to programme and fund allocation.
                  </p>
                  <input
                    type="file"
                    accept=".pdf,application/pdf"
                    onChange={e => setApprovalFile(e.target.files?.[0] ?? null)}
                    className="mt-2 block w-full text-xs text-stone-600 file:mr-3 file:rounded-lg file:border-0 file:bg-[#7a1b32] file:px-3 file:py-2 file:text-xs file:font-semibold file:text-white hover:file:bg-[#631628]"
                  />
                  {approvalFile && (
                    <p className="mt-1 text-xs font-medium text-emerald-700">
                      ✓ Attached: {approvalFile.name} ({(approvalFile.size / 1024).toFixed(1)} KB)
                    </p>
                  )}
                </div>

                {/* 7. Hall(s) required for the Event */}
                <div className="space-y-2">
                  <label className="block text-sm font-semibold text-stone-800">
                    7. Hall(s) required for the Event <span className="text-rose-600">*</span>
                  </label>
                  <p className="text-xs text-stone-500">
                    Select primary venue for deterministic schedule conflict verification against campus booking engine.
                  </p>
                  <select value={venue} onChange={e => setVenue(e.target.value)} className={inputStyle}>
                    <option value="">Select Hall / Venue</option>
                    {venues.data?.items.map(v => (
                      <option key={v.id} value={v.id}>
                        {v.name} {v.capacity ? `(Cap: ${v.capacity})` : ''} · {v.availability_state}
                      </option>
                    ))}
                  </select>
                  <RemoteState signedIn={Boolean(token)} {...venues} />
                  
                  {/* Additional hall requirements from official form list */}
                  <div className="mt-2 space-y-1">
                    <span className="text-xs font-medium text-stone-600">Additional Parallel Halls (Form Section 7):</span>
                    <div className="grid grid-cols-2 gap-2 text-xs text-stone-700 sm:grid-cols-3">
                      {[
                        'New Auditorium / Pandal',
                        'Amriteswari Hall',
                        'Sudhamani Hall',
                        'Seminar Halls I & II',
                        'Acharya Hall / AB-1',
                        'Sandeepani Hall / AB II',
                        'Anugraha Hall AB III'
                      ].map(hallName => {
                        const checked = additionalHalls.includes(hallName);
                        return (
                          <label key={hallName} className="flex items-center gap-1.5 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={e => {
                                if (e.target.checked) setAdditionalHalls([...additionalHalls, hallName]);
                                else setAdditionalHalls(additionalHalls.filter(h => h !== hallName));
                              }}
                              className="rounded text-[#7a1b32] focus:ring-[#7a1b32]"
                            />
                            <span>{hallName}</span>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* 8. Other Campus Infrastructure */}
                <div className="space-y-1">
                  <label className="block text-sm font-semibold text-stone-800">
                    8. Other Campus Infrastructure
                  </label>
                  <input
                    placeholder="Playground / Boys Common Hall / Parking etc."
                    value={otherInfrastructure}
                    onChange={e => setOtherInfrastructure(e.target.value)}
                    className={inputStyle}
                  />
                </div>

                {/* 9. Audio / video / Visual requirement for Parallel Sessions */}
                <div className="space-y-1">
                  <label className="block text-sm font-semibold text-stone-800">
                    9. Audio / video / Visual requirement for Parallel Sessions
                  </label>
                  <textarea
                    rows={2}
                    placeholder="e.g. Wireless mics, projector with HDMI, PA sound system in Seminar Hall 1"
                    value={avRequirements}
                    onChange={e => setAvRequirements(e.target.value)}
                    className={inputStyle}
                  />
                </div>

                {/* 10. Requirement of Food & Refreshments */}
                <div className="space-y-2 rounded-xl border border-stone-200 bg-stone-50/60 p-4">
                  <div className="flex items-center justify-between">
                    <label className="block text-sm font-semibold text-stone-800">
                      10. Requirement of Food & Refreshments
                    </label>
                    <button
                      type="button"
                      onClick={() => setFoodRows([...foodRows, { date: '', breakfast: false, tea11am: false, tea3pm: false, lunch: false, dinner: false, count: '' }])}
                      className="rounded-lg border border-stone-300 bg-white px-2.5 py-1 text-xs font-semibold text-stone-700 shadow-2xs hover:bg-stone-50"
                    >
                      + Add Date Row
                    </button>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-stone-200 text-stone-600">
                          <th className="py-2 pr-2">Date</th>
                          <th className="p-2 text-center">Breakfast</th>
                          <th className="p-2 text-center">Tea @ 11 AM</th>
                          <th className="p-2 text-center">Tea @ 3 PM</th>
                          <th className="p-2 text-center">Lunch</th>
                          <th className="p-2 text-center">Dinner</th>
                          <th className="py-2 pl-2 text-right">No. of persons</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-stone-200/60">
                        {foodRows.map((row, idx) => (
                          <tr key={idx}>
                            <td className="py-2 pr-2">
                              <input
                                type="date"
                                value={row.date}
                                onChange={e => {
                                  const updated = [...foodRows];
                                  updated[idx].date = e.target.value;
                                  setFoodRows(updated);
                                }}
                                className="rounded border border-stone-300 p-1 text-xs"
                              />
                            </td>
                            <td className="p-2 text-center">
                              <input
                                type="checkbox"
                                checked={row.breakfast}
                                onChange={e => {
                                  const updated = [...foodRows];
                                  updated[idx].breakfast = e.target.checked;
                                  setFoodRows(updated);
                                }}
                              />
                            </td>
                            <td className="p-2 text-center">
                              <input
                                type="checkbox"
                                checked={row.tea11am}
                                onChange={e => {
                                  const updated = [...foodRows];
                                  updated[idx].tea11am = e.target.checked;
                                  setFoodRows(updated);
                                }}
                              />
                            </td>
                            <td className="p-2 text-center">
                              <input
                                type="checkbox"
                                checked={row.tea3pm}
                                onChange={e => {
                                  const updated = [...foodRows];
                                  updated[idx].tea3pm = e.target.checked;
                                  setFoodRows(updated);
                                }}
                              />
                            </td>
                            <td className="p-2 text-center">
                              <input
                                type="checkbox"
                                checked={row.lunch}
                                onChange={e => {
                                  const updated = [...foodRows];
                                  updated[idx].lunch = e.target.checked;
                                  setFoodRows(updated);
                                }}
                              />
                            </td>
                            <td className="p-2 text-center">
                              <input
                                type="checkbox"
                                checked={row.dinner}
                                onChange={e => {
                                  const updated = [...foodRows];
                                  updated[idx].dinner = e.target.checked;
                                  setFoodRows(updated);
                                }}
                              />
                            </td>
                            <td className="py-2 pl-2 text-right">
                              <input
                                type="number"
                                min="0"
                                placeholder="Count"
                                value={row.count}
                                onChange={e => {
                                  const updated = [...foodRows];
                                  updated[idx].count = e.target.value;
                                  setFoodRows(updated);
                                }}
                                className="w-20 rounded border border-stone-300 p-1 text-right text-xs"
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 11. Vehicle Requirements */}
                <div className="space-y-2 rounded-xl border border-stone-200 bg-stone-50/60 p-4">
                  <div className="flex items-center justify-between">
                    <label className="block text-sm font-semibold text-stone-800">
                      11. Vehicle Requirements (If any)
                    </label>
                    <button
                      type="button"
                      onClick={() => setVehicleRows([...vehicleRows, { date: '', vehicleType: '' }])}
                      className="rounded-lg border border-stone-300 bg-white px-2.5 py-1 text-xs font-semibold text-stone-700 shadow-2xs hover:bg-stone-50"
                    >
                      + Add Vehicle
                    </button>
                  </div>
                  <div className="space-y-2">
                    {vehicleRows.map((vRow, idx) => (
                      <div key={idx} className="flex gap-2">
                        <input
                          type="date"
                          value={vRow.date}
                          onChange={e => {
                            const updated = [...vehicleRows];
                            updated[idx].date = e.target.value;
                            setVehicleRows(updated);
                          }}
                          className="rounded border border-stone-300 p-1 text-xs"
                        />
                        <input
                          placeholder="Type of vehicle (e.g. Innova / Campus Bus / 14-seater)"
                          value={vRow.vehicleType}
                          onChange={e => {
                            const updated = [...vehicleRows];
                            updated[idx].vehicleType = e.target.value;
                            setVehicleRows(updated);
                          }}
                          className="flex-1 rounded border border-stone-300 p-1 text-xs"
                        />
                      </div>
                    ))}
                  </div>
                </div>

                {/* 12. Number of Guest rooms & Hostel rooms required */}
                <div className="space-y-2 rounded-xl border border-stone-200 bg-stone-50/60 p-4">
                  <label className="block text-sm font-semibold text-stone-800">
                    12. Number of Guest rooms & Hostel rooms required
                  </label>
                  <p className="text-xs text-stone-500">
                    Chargeable through Project/Seed grant. If not attach Sanction letter from Dean of School if this facility is to be provided by the University.
                  </p>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <label className="text-xs font-medium text-stone-700">
                      Guest House (AC)
                      <input
                        type="number"
                        min="0"
                        placeholder="0"
                        value={guestHouseAc}
                        onChange={e => setGuestHouseAc(e.target.value)}
                        className={inputStyle}
                      />
                    </label>
                    <label className="text-xs font-medium text-stone-700">
                      Annexe (AC)
                      <input
                        type="number"
                        min="0"
                        placeholder="0"
                        value={annexeAc}
                        onChange={e => setAnnexeAc(e.target.value)}
                        className={inputStyle}
                      />
                    </label>
                    <label className="text-xs font-medium text-stone-700">
                      Hostel Rooms (Boys)
                      <input
                        type="number"
                        min="0"
                        placeholder="0"
                        value={hostelBoys}
                        onChange={e => setHostelBoys(e.target.value)}
                        className={inputStyle}
                      />
                    </label>
                    <label className="text-xs font-medium text-stone-700">
                      Hostel Rooms (Girls)
                      <input
                        type="number"
                        min="0"
                        placeholder="0"
                        value={hostelGirls}
                        onChange={e => setHostelGirls(e.target.value)}
                        className={inputStyle}
                      />
                    </label>
                  </div>
                </div>

                {/* 13. Publicity */}
                <div className="space-y-3 rounded-xl border border-stone-200 bg-stone-50/60 p-4">
                  <label className="block text-sm font-semibold text-stone-800">
                    13. Publicity
                  </label>
                  <p className="text-xs text-stone-500">
                    (a) Flex by Events dept (Logo, photos and matter for designing flex by Events dept to be provided by User dept one week in advance).
                  </p>
                  <div className="space-y-1.5 text-xs text-stone-700">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={flexMainGate}
                        onChange={e => setFlexMainGate(e.target.checked)}
                        className="rounded text-[#7a1b32]"
                      />
                      <span>(i) Flex board at Main Gate</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={flexVenue}
                        onChange={e => setFlexVenue(e.target.checked)}
                        className="rounded text-[#7a1b32]"
                      />
                      <span>(ii) Flex board at venue</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={flexDigitalBackdrop}
                        onChange={e => setFlexDigitalBackdrop(e.target.checked)}
                        className="rounded text-[#7a1b32]"
                      />
                      <span>(iii) Flex Backdrop at venue (Preferable to use digital backdrop)</span>
                    </label>
                  </div>
                  <div className="grid gap-3 pt-2 sm:grid-cols-2 text-xs">
                    <div className="flex items-center justify-between rounded-lg border border-stone-200 bg-white p-2.5">
                      <span className="font-medium text-stone-700">(b) Photography / Videography by AOC</span>
                      <div className="flex gap-2">
                        {(['YES', 'NO'] as const).map(opt => (
                          <button
                            key={opt}
                            type="button"
                            onClick={() => setPhotographyAoc(opt)}
                            className={`rounded px-2.5 py-1 text-xs font-semibold ${photographyAoc === opt ? 'bg-[#7a1b32] text-white' : 'border border-stone-200 bg-stone-50 text-stone-700'}`}
                          >
                            {opt}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div className="flex items-center justify-between rounded-lg border border-stone-200 bg-white p-2.5">
                      <span className="font-medium text-stone-700">(c) Media Coverage by AOC</span>
                      <div className="flex gap-2">
                        {(['YES', 'NO'] as const).map(opt => (
                          <button
                            key={opt}
                            type="button"
                            onClick={() => setMediaCoverageAoc(opt)}
                            className={`rounded px-2.5 py-1 text-xs font-semibold ${mediaCoverageAoc === opt ? 'bg-[#7a1b32] text-white' : 'border border-stone-200 bg-stone-50 text-stone-700'}`}
                          >
                            {opt}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* 14. Funding of the Event */}
                <div className="space-y-1">
                  <label className="block text-sm font-semibold text-stone-800">
                    14. Funding of the Event (By University / Funded / On payment basis)
                  </label>
                  <select value={fundingSource} onChange={e => setFundingSource(e.target.value)} className={inputStyle}>
                    <option value="By University">By University</option>
                    <option value="Funded (Grant / Sponsorship)">Funded (Grant / Sponsorship)</option>
                    <option value="On payment basis (Registration fees)">On payment basis (Registration fees)</option>
                    <option value="Seed Grant">Seed Grant</option>
                  </select>
                </div>

                {/* 15. Additional requirements */}
                <div className="space-y-1">
                  <label className="block text-sm font-semibold text-stone-800">
                    15. Any additional requirements – please mention
                  </label>
                  <textarea
                    rows={2}
                    placeholder="Provide any further remarks, special security requirements, VIP protocols, etc."
                    value={additionalNotes}
                    onChange={e => setAdditionalNotes(e.target.value)}
                    className={inputStyle}
                  />
                </div>

                {/* Program Description / Abstract */}
                <div className="space-y-1">
                  <label className="block text-sm font-semibold text-stone-800">
                    Programme Abstract & Agenda Overview
                  </label>
                  <textarea
                    rows={3}
                    placeholder="Brief agenda, guest speaker details, and schedule overview"
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                    className={inputStyle}
                  />
                </div>

                {/* Validation Banner */}
                {validation && <p role="alert" className="text-sm font-medium text-rose-800">{validation}</p>}

                {/* Submit Action Button */}
                <button
                  type="submit"
                  disabled={!payload || saving}
                  className="w-full rounded-[10px] bg-[#7a1b32] px-6 py-3.5 text-base font-bold text-white shadow-sm transition-all duration-150 ease-out hover:bg-[#631628] active:scale-[0.98] disabled:opacity-50"
                >
                  {saving ? 'Submitting Facility Booking…' : 'Submit Facility Booking Form'}
                </button>
              </fieldset>

              {error && <p role="alert" className="text-sm font-medium text-rose-800">{error}</p>}

              {created && (
                <div role="status" className="rounded-xl border border-emerald-200 bg-emerald-50/90 p-5 text-sm text-emerald-950 space-y-2">
                  <div className="flex items-center gap-2 font-bold text-emerald-900">
                    <span>✓ Facility Booking Form Submitted</span>
                    <span className="rounded-full bg-emerald-200/80 px-2 py-0.5 text-xs text-emerald-800">{created.event.status}</span>
                  </div>
                  <p className="text-xs text-emerald-800">
                    Draft recorded for <strong>{created.event.title}</strong>. A tentative proposal is not a confirmed booking. It now enters the two-stage review pipeline (Faculty Advisor → Campus Director / OSA Approval).
                  </p>
                  <Link className="inline-block text-xs font-bold text-[#7a1b32] underline hover:text-[#631628]" href={'/changes?eventId=' + created.event.id}>
                    Open Event Workspace and Track Approval Stages →
                  </Link>
                </div>
              )}
            </form>

            <ConflictSidebar
              result={created ? {
                event_id: created.event.id,
                evaluated_as: created.event.status,
                has_blocking: created.conflicts.some(c => c.severity === 'blocking'),
                conflicts: created.conflicts,
                checked_at: created.event.created_at
              } : preview.data}
              loading={preview.loading}
              error={preview.error}
            />
          </div>

          {created && (
            <div className="mt-8">
              <h2 className="text-xl font-bold text-stone-900 mb-2">Upload Supplementary Proposal Documents</h2>
              <ProposalUpload key={token + created.event.id} eventId={created.event.id} clubId={created.event.club_id} />
            </div>
          )}
        </>
      )}
    </section>
  );
}
