'use client';
export default function ErrorBoundary({ retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return <section className="mx-auto max-w-xl p-8"><h1 className="text-2xl font-bold">This view could not load</h1><p className="my-4">Try loading it again.</p><button className="rounded-xl bg-[#7a1b32] px-5 py-3 text-white" onClick={retry}>Try again</button></section>;
}
