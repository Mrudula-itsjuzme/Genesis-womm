import { BarChart2 } from 'lucide-react';
import ChangeImpactList from '@/components/ChangeImpactList';

export default function ChangesPage() {
    return (
        <div className="mt-16 min-h-[calc(100vh-4rem)] bg-[#F5EEE9] px-5 py-7 sm:px-8 lg:px-10">
            <div className="mx-auto max-w-6xl">
                <header className="mb-7 border-b border-rose-200/70 pb-6">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-rose-100 bg-rose-50 text-[#7a1b32]">
                            <BarChart2 className="h-5 w-5" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900">Change Impact</h1>
                            <p className="mt-0.5 text-sm text-gray-600">Preview how a date, time, or venue change affects the shared schedule.</p>
                        </div>
                    </div>
                </header>
                <ChangeImpactList />
            </div>
        </div>
    );
}
