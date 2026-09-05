import type { CheckKind, Metric, Verdict } from "./types";

/** 63.4 -> "1:03.4" (tenths only when useful). */
export function timecode(seconds: number | null | undefined, precise = false): string {
  if (seconds == null || Number.isNaN(seconds)) return "—:—";
  const clamped = Math.max(seconds, 0);
  const m = Math.floor(clamped / 60);
  const s = Math.floor(clamped % 60);
  const base = `${m}:${s.toString().padStart(2, "0")}`;
  if (!precise) return base;
  const tenths = Math.floor((clamped % 1) * 10);
  return `${base}.${tenths}`;
}

export function bytes(size: number): string {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(0)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function percent(value: number): string {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

/** Non-colour cue so verdicts never rely on hue alone. */
export const VERDICT_GLYPH: Record<Verdict, string> = {
  PASS: "✓",
  FAIL: "✕",
  REVIEW: "?",
};

export const VERDICT_MEANING: Record<Verdict, string> = {
  PASS: "Evidence supports the requested revision.",
  FAIL: "Evidence contradicts the requested revision.",
  REVIEW: "EditDiff will not claim certainty it cannot prove.",
};

const KIND_LABELS: Record<string, string> = {
  mute_audio: "Audio",
  visual_change: "Visual",
  remove_pause: "Timing",
  text_change: "On-screen text",
  zoom_crop: "Framing",
  generic: "Unclassified",
};

export function kindLabel(kind: CheckKind): string {
  return KIND_LABELS[kind] ?? String(kind).replace(/_/g, " ");
}

export function metricLabel(name: string): string {
  return name.replace(/_/g, " ");
}

export function metricValue(value: Metric["v1"], unit?: string | null): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") {
    if (unit === "seconds") return `${value.toFixed(2)}s`;
    if (Math.abs(value) >= 100) return value.toFixed(1);
    return value.toFixed(3);
  }
  return String(value);
}

export function signedDelta(delta: number | null | undefined): string {
  if (delta === null || delta === undefined || Number.isNaN(delta)) return "—";
  const sign = delta > 0 ? "+" : "";
  return `${sign}${Math.abs(delta) >= 100 ? delta.toFixed(1) : delta.toFixed(3)}`;
}
