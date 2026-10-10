'use client';

import { FormEvent, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, ExternalLink, Printer } from 'lucide-react';

const hallOptions = [
    'New Auditorium / Pandal',
    'Amriteshwari Hall',
    'Sudhamani Hall',
    'Seminar Halls I & II',
    'Acharya Hall / AB-1',
    'Sandeepani Hall / AB II',
    'Anugraha Hall / AB III',
];

const ictSupportOptions = [
    { id: 'audiovisual', label: 'Audio/visual equipment or technician', email: 'audiovisual@cb.amrita.edu' },
    { id: 'lab-scheduling', label: 'Computer lab scheduling', email: 'computerlabs@cb.amrita.edu' },
    { id: 'wifi', label: 'Campus Wi-Fi support', email: 'campuswifi@cb.amrita.edu' },
    { id: 'video-conferencing', label: 'E-learning or video-conferencing setup', email: 'elearning@cb.amrita.edu' },
];

const inputClass = 'mt-1 block w-full min-w-0 rounded-md border border-stone-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-[#7a1b32] focus:ring-2 focus:ring-rose-100';
const labelClass = 'block min-w-0 text-sm font-semibold text-gray-700';

export default function PlanEventPage() {
    const [selectedSupport, setSelectedSupport] = useState<string[]>([]);
    const [requestPrepared, setRequestPrepared] = useState(false);

    const toggleSupport = (id: string) => {
        setRequestPrepared(false);
        setSelectedSupport((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
    };

    const prepareRequest = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setRequestPrepared(true);
    };

    return (
        <div className="mt-16 min-h-[calc(100vh-4rem)] bg-[#F5EEE9] px-5 py-7 sm:px-8 lg:px-10 print:mt-0 print:min-h-0 print:bg-white print:px-0 print:py-0">
            <div className="mx-auto max-w-5xl">
                <Link href="/calendar" className="inline-flex items-center gap-2 text-sm font-semibold text-[#7a1b32] hover:text-[#541224] print:hidden">
                    <ArrowLeft className="h-4 w-4" /> Calendar
                </Link>
                <header className="mb-7 mt-5 border-b border-rose-200/70 pb-6">
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#7a1b32]">Facility request · Coimbatore campus</p>
                    <h1 className="mt-2 text-3xl font-bold tracking-tight text-gray-900">Facility Booking Request</h1>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-600">Complete the event requirements below, then print the request for submission to the Events Department. This page does not reserve a facility or grant approval.</p>
                    <a href="https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf" target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-[#7a1b32] underline decoration-rose-200 underline-offset-2 hover:text-[#541224] print:hidden">
                        Official revised facility-booking form · OSA Handbook, pp. 24–26 <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                </header>

                <form onSubmit={prepareRequest} className="divide-y divide-stone-300">
                    <section className="py-7" aria-labelledby="event-details-heading">
                        <h2 id="event-details-heading" className="mb-5 text-lg font-bold text-gray-900">1–6. Event details and academic approval</h2>
                        <div className="grid grid-cols-1 gap-x-5 gap-y-4 sm:grid-cols-2">
                            <label className={`${labelClass} sm:col-span-2`}>1. Name of the event<input required name="eventName" className={inputClass} /></label>
                            <label className={labelClass}>2. Department organizing the event<input required name="organizingDepartment" className={inputClass} /></label>
                            <fieldset className="grid grid-cols-2 gap-3">
                                <legend className={labelClass}>3. Date(s) of event</legend>
                                <label className="text-xs font-medium text-gray-600">From<input required name="startDate" type="date" aria-label="Event start date" className={inputClass} /></label>
                                <label className="text-xs font-medium text-gray-600">To<input required name="endDate" type="date" aria-label="Event end date" className={inputClass} /></label>
                            </fieldset>
                            <label className={labelClass}>4. Organizing secretary / faculty / staff responsible<input required name="responsiblePerson" className={inputClass} /></label>
                            <label className={labelClass}>Mobile number<input required name="contactMobile" type="tel" autoComplete="tel" className={inputClass} /></label>
                            <fieldset className="sm:col-span-2">
                                <legend className={labelClass}>5. Approximate number of participants</legend>
                                <label className={`${labelClass} mt-3 max-w-xs`}>Total<input name="participantsTotal" type="number" min="0" placeholder="0" className={inputClass} /></label>
                                <div className="mt-2 grid grid-cols-[minmax(90px,1fr)_1fr_1fr] gap-x-3 gap-y-2 text-xs font-semibold text-gray-600">
                                    <span /> <span>Male</span> <span>Female</span>
                                    <span className="self-center">National</span><input name="nationalMale" type="number" min="0" aria-label="National male participants" placeholder="0" className={inputClass} /><input name="nationalFemale" type="number" min="0" aria-label="National female participants" placeholder="0" className={inputClass} />
                                    <span className="self-center">International</span><input name="internationalMale" type="number" min="0" aria-label="International male participants" placeholder="0" className={inputClass} /><input name="internationalFemale" type="number" min="0" aria-label="International female participants" placeholder="0" className={inputClass} />
                                </div>
                            </fieldset>
                            <label className={`${labelClass} sm:col-span-2`}>6. Academic approval copy from Dean of School
                                <input name="academicApproval" type="file" accept=".pdf,.jpg,.jpeg,.png" className="mt-2 block w-full text-sm text-gray-600 file:mr-3 file:rounded-md file:border-0 file:bg-[#fff5f0] file:px-3 file:py-2 file:text-xs file:font-bold file:text-[#7a1b32]" />
                                <span className="mt-1 block text-xs font-normal text-gray-500">Attach the approval copy when submitting the official request.</span>
                            </label>
                        </div>
                    </section>

                    <section className="py-7" aria-labelledby="facility-heading">
                        <h2 id="facility-heading" className="mb-5 text-lg font-bold text-gray-900">7–9. Facility and technical requirements</h2>
                        <fieldset>
                            <legend className={labelClass}>7. Hall(s) required for the event</legend>
                            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                                {hallOptions.map((hall) => <label key={hall} className="flex min-w-0 items-start gap-2 py-1 text-sm text-gray-700"><input type="checkbox" name="halls" value={hall} className="mt-0.5 h-4 w-4 shrink-0 accent-[#7a1b32]" /><span>{hall}</span></label>)}
                            </div>
                            <label className={`${labelClass} mt-4`}>Other hall requested<input name="otherHall" className={inputClass} /></label>
                        </fieldset>
                        <label className={`${labelClass} mt-5`}>8. Other campus infrastructure (playground, boys common hall, parking, etc.)<textarea name="otherInfrastructure" rows={2} className={inputClass} /></label>
                        <label className={`${labelClass} mt-5`}>9. Audio / video / visual requirements for parallel sessions<textarea name="avRequirements" rows={3} placeholder="Equipment, room, session, or technician requirements" className={inputClass} /></label>
                        <fieldset className="mt-5">
                            <legend className={labelClass}>ICTS support to contact, if required</legend>
                            <p className="mt-1 text-xs leading-5 text-gray-500">Select support needed, then contact the published service channel directly. CampusCue does not send the request.</p>
                            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                                {ictSupportOptions.map((option) => {
                                    const checked = selectedSupport.includes(option.id);
                                    return <div key={option.id} className="flex min-w-0 items-start gap-2 py-1"><input id={`support-${option.id}`} type="checkbox" checked={checked} onChange={() => toggleSupport(option.id)} className="mt-0.5 h-4 w-4 shrink-0 accent-[#7a1b32]" /><label htmlFor={`support-${option.id}`} className="min-w-0 flex-1 text-sm text-gray-700">{option.label}</label>{checked && <a href={`mailto:${option.email}?subject=Event%20support%20request`} className="break-all text-xs font-semibold text-[#7a1b32] underline underline-offset-2">{option.email}</a>}</div>;
                                })}
                            </div>
                            <a href="https://intranet.cb.amrita.edu/infrastructure/icts/support-contacts" target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-[#7a1b32] underline underline-offset-2 print:hidden">Official ICTS support contacts <ExternalLink className="h-3 w-3" /></a>
                        </fieldset>
                    </section>

                    <section className="py-7" aria-labelledby="food-heading">
                        <h2 id="food-heading" className="mb-2 text-lg font-bold text-gray-900">10. Food and refreshments</h2>
                        <p className="mb-4 text-xs leading-5 text-gray-600">Tick each requirement for the applicable date and enter the number of persons.</p>
                        <div className="w-full min-w-0 max-w-full overflow-x-auto">
                            <table className="w-full min-w-[680px] border-collapse text-left text-xs">
                                <thead><tr className="bg-[#efe5df] text-gray-700"><th className="border border-stone-300 p-2">Date</th><th className="border border-stone-300 p-2">Breakfast</th><th className="border border-stone-300 p-2">Tea &amp; snacks<br />11 AM / 3 PM</th><th className="border border-stone-300 p-2">Lunch</th><th className="border border-stone-300 p-2">Dinner</th><th className="border border-stone-300 p-2">No. persons</th></tr></thead>
                                <tbody>{[0, 1, 2].map((row) => <tr key={row}>
                                    <td className="border border-stone-300 p-1"><input type="date" name={`refreshmentDate${row + 1}`} aria-label={`Refreshment date ${row + 1}`} className="w-full min-w-32 rounded border-0 px-2 py-2 text-xs" /></td>
                                    {['Breakfast', 'Tea and snacks', 'Lunch', 'Dinner'].map((meal) => <td key={meal} className="border border-stone-300 p-2 text-center"><input type="checkbox" name={`refreshments${row + 1}`} value={meal} aria-label={`${meal} on refreshment date ${row + 1}`} className="h-4 w-4 accent-[#7a1b32]" /></td>)}
                                    <td className="border border-stone-300 p-1"><input type="number" min="0" name={`refreshmentPersons${row + 1}`} aria-label={`Number of persons for refreshment date ${row + 1}`} className="w-full rounded border-0 px-2 py-2 text-xs" /></td>
                                </tr>)}</tbody>
                            </table>
                        </div>
                    </section>

                    <section className="py-7" aria-labelledby="logistics-heading">
                        <h2 id="logistics-heading" className="mb-5 text-lg font-bold text-gray-900">11–12. Transport and accommodation</h2>
                        <fieldset className="min-w-0">
                            <legend className={labelClass}>11. Vehicle requirements (if any)</legend>
                            <div className="mt-2 w-full min-w-0 max-w-full overflow-x-auto">
                                <table className="w-full min-w-[440px] border-collapse text-left text-xs">
                                    <thead><tr className="bg-[#efe5df] text-gray-700"><th className="border border-stone-300 p-2">Date(s)</th><th className="border border-stone-300 p-2">Type of vehicle / quantity</th></tr></thead>
                                    <tbody>{[0, 1, 2].map((row) => <tr key={row}><td className="border border-stone-300 p-1"><input type="date" name={`vehicleDate${row + 1}`} aria-label={`Vehicle date ${row + 1}`} className="w-full rounded border-0 px-2 py-2 text-xs" /></td><td className="border border-stone-300 p-1"><input name={`vehicleType${row + 1}`} aria-label={`Vehicle type ${row + 1}`} className="w-full rounded border-0 px-2 py-2 text-xs" /></td></tr>)}</tbody>
                                </table>
                            </div>
                        </fieldset>
                        <fieldset className="mt-5">
                            <legend className={labelClass}>12. Number of guest and hostel rooms required</legend>
                            <p className="mt-1 text-xs leading-5 text-gray-500">Rooms are chargeable through the project/seed grant. Attach the Dean of School sanction letter if university-provided rooms are requested.</p>
                            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">{['Guest House (AC)', 'Annexe (A/C)', 'Hostel Rooms (Boys)', 'Hostel Rooms (Girls)'].map((room) => <label key={room} className={labelClass}>{room}<input type="number" min="0" name={`rooms-${room}`} className={inputClass} /></label>)}</div>
                        </fieldset>
                    </section>

                    <section className="py-7" aria-labelledby="publicity-heading">
                        <h2 id="publicity-heading" className="mb-5 text-lg font-bold text-gray-900">13. Publicity and media</h2>
                        <fieldset>
                            <legend className={labelClass}>Flex by Events Department</legend>
                            <p className="mt-1 text-xs leading-5 text-gray-500">Provide the logo, photos, and matter for Events Department design one week in advance.</p>
                            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">{['Flex board at Main Gate', 'Flex board at venue', 'Flex backdrop at venue'].map((item) => <label key={item} className="flex items-center gap-2 text-sm text-gray-700"><input type="checkbox" name="publicityLocations" value={item} className="h-4 w-4 accent-[#7a1b32]" />{item}</label>)}</div>
                            <label className={`${labelClass} mt-4 max-w-sm`}>Required format<select name="publicityFormat" defaultValue="" className={inputClass}><option value="">Select if needed</option><option>Digital</option><option>Flex</option><option>Digital and Flex</option></select></label>
                        </fieldset>
                        <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
                            {['Photography / Videography by AOC', 'Media coverage by AOC'].map((service, index) => <fieldset key={service}><legend className={labelClass}>{service}</legend><div className="mt-2 flex gap-5 text-sm text-gray-700"><label className="flex items-center gap-2"><input type="radio" name={`media-${index}`} value="Yes" className="h-4 w-4 accent-[#7a1b32]" />Yes</label><label className="flex items-center gap-2"><input type="radio" name={`media-${index}`} value="No" className="h-4 w-4 accent-[#7a1b32]" />No</label></div></fieldset>)}
                        </div>
                    </section>

                    <section className="py-7" aria-labelledby="funding-heading">
                        <h2 id="funding-heading" className="mb-5 text-lg font-bold text-gray-900">14–15. Funding and additional requirements</h2>
                        <fieldset>
                            <legend className={labelClass}>14. Funding of the event</legend>
                            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2 text-sm text-gray-700">{['University funded', 'On payment basis', 'Other funding'].map((basis) => <label key={basis} className="flex items-center gap-2"><input type="radio" name="fundingBasis" value={basis} className="h-4 w-4 accent-[#7a1b32]" />{basis}</label>)}</div>
                            <label className={`${labelClass} mt-4`}>Please mention funding details<textarea name="fundingDetails" rows={2} className={inputClass} /></label>
                        </fieldset>
                        <label className={`${labelClass} mt-5`}>15. Additional requirements<textarea name="additionalRequirements" rows={4} placeholder="List any additional requirements. Attach separate sheets if needed." className={inputClass} /></label>
                        <label className={`${labelClass} mt-4`}>Supporting sheets or documents
                            <input name="supportingDocuments" type="file" multiple className="mt-2 block w-full text-sm text-gray-600 file:mr-3 file:rounded-md file:border-0 file:bg-[#fff5f0] file:px-3 file:py-2 file:text-xs file:font-bold file:text-[#7a1b32]" />
                            <span className="mt-1 block text-xs font-normal text-gray-500">Attachments remain in this browser and must be submitted separately with the printed request.</span>
                        </label>
                    </section>

                    <section className="py-7" aria-labelledby="signoff-heading">
                        <h2 id="signoff-heading" className="mb-4 text-lg font-bold text-gray-900">Organizer declaration and official processing</h2>
                        <label className="flex items-start gap-2 text-sm leading-6 text-gray-700"><input required type="checkbox" name="organizerDeclaration" className="mt-1 h-4 w-4 shrink-0 accent-[#7a1b32]" />I confirm these are event requirements submitted for review; this request is not an approval or venue booking.</label>
                        <div className="mt-5 grid grid-cols-1 gap-3 border-t border-stone-200 pt-4 sm:grid-cols-3">
                            <p className="text-sm"><span className="block font-bold text-gray-800">Organizer / Coordinator</span><span className="text-xs text-gray-600">Name and signature required on printed request</span></p>
                            <p className="text-sm"><span className="block font-bold text-gray-800">Events Department Manager</span><span className="text-xs text-amber-800">Pending office review</span></p>
                            <p className="text-sm"><span className="block font-bold text-gray-800">Campus Director</span><span className="text-xs text-amber-800">Approval pending</span></p>
                        </div>
                    </section>

                    <section className="border-t border-stone-300 py-6 print:hidden" aria-label="Request actions">
                        <p className="mb-4 text-xs leading-5 text-gray-600">CampusCue does not submit this request. Print and submit it with the required attachments to the Events Department. The venue remains unconfirmed until authorized approval is recorded.</p>
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                            <button type="submit" className="rounded-lg bg-[#7a1b32] px-5 py-3 text-sm font-bold text-white hover:bg-[#5a1222]">Prepare booking request</button>
                            {requestPrepared && <><button type="button" onClick={() => window.print()} className="inline-flex items-center justify-center gap-2 rounded-lg border border-stone-300 bg-white px-4 py-3 text-sm font-semibold text-gray-800 hover:border-[#7a1b32]"><Printer className="h-4 w-4" />Print request</button><p role="status" className="text-sm font-semibold text-emerald-800">Request prepared. It has not been submitted or approved.</p></>}
                        </div>
                    </section>
                </form>
            </div>
        </div>
    );
}