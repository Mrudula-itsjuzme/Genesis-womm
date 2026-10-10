export function validateProposal(file: Pick<File, 'name' | 'size' | 'type'>): string | null {
  if (!file.name.toLowerCase().endsWith('.pdf') || (file.type && file.type !== 'application/pdf')) return 'Select a PDF document.';
  if (file.size <= 0 || file.size > 15 * 1024 * 1024) return 'PDF size must be between 1 byte and 15 MiB.';
  return null;
}
