export function sourceUrl(raw: string | null | undefined): string | null {
  if (!raw) return null;
  try { const url = new URL(raw); return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null; }
  catch { return null; }
}
