/**
 * Client-side preview of how the backend will split revision notes.
 * Mirrors backend/app/notes.py closely enough to preview counts and
 * timestamps; the backend parse remains authoritative.
 */
const TIMESTAMP = /(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:\.(\d+))?|(\d+(?:\.\d+)?)\s*s\b/i;

export type NoteLine = { text: string; seconds: number | null };

export function previewNotes(notes: string): NoteLine[] {
  return notes
    .split(/\r?\n/)
    .map((line) => line.replace(/^[\s\t\-*•]+|[\s\t\-*•]+$/g, ""))
    .filter(Boolean)
    .map((text) => ({ text, seconds: timestampOf(text) }));
}

export function timestampOf(text: string): number | null {
  const match = TIMESTAMP.exec(text);
  if (!match) return null;
  if (match[5]) return Number(match[5]);
  const h = Number(match[1] ?? 0);
  const m = Number(match[2] ?? 0);
  const s = Number(match[3] ?? 0);
  const frac = match[4] ? Number(`0.${match[4]}`) : 0;
  return h * 3600 + m * 60 + s + frac;
}
