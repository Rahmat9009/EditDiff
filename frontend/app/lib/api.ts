import { isDiscoverReport, isReport, type DiscoverReport, type Report } from "./types";

/** Public base URL of the EditDiff API. Never put secrets in NEXT_PUBLIC_*. */
export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

/** Absolute URL for an evidence asset returned as an API-relative path. */
export function assetUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (/^(https?:|data:)/i.test(path)) return path;
  return `${API_BASE}${path.startsWith("/") ? "" : "/"}${path}`;
}

export class ApiError extends Error {
  readonly offline: boolean;
  constructor(message: string, offline = false) {
    super(message);
    this.name = "ApiError";
    this.offline = offline;
  }
}

const OFFLINE_HINT = `Cannot reach the EditDiff API at ${API_BASE}. Start the backend, or point NEXT_PUBLIC_API_URL at the running instance.`;

export async function checkHealth(signal?: AbortSignal): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, { signal, cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function analyze(
  v1: File,
  v2: File,
  notes: string,
  signal?: AbortSignal,
): Promise<Report> {
  const body = new FormData();
  body.append("v1", v1);
  body.append("v2", v2);
  body.append("notes", notes);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/analyze`, { method: "POST", body, signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(OFFLINE_HINT, true);
  }

  let payload: unknown = null;
  try {
    payload = await res.json();
  } catch {
    payload = null;
  }

  if (!res.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : `Analysis failed (HTTP ${res.status}).`;
    throw new ApiError(detail);
  }

  if (!isReport(payload)) {
    throw new ApiError("The API responded, but the report was not in the expected format.");
  }
  return payload;
}

/** Download the persisted JSON report; fallback is only for an actual failure. */
export async function fetchAuditExport(report: Report): Promise<Blob | null> {
  try {
    const res = await fetch(`${API_BASE}/reports/${encodeURIComponent(report.report_id)}/export`, {
      cache: "no-store",
    });
    if (!res.ok || !res.headers.get("content-type")?.includes("application/json")) return null;
    const blob = await res.blob();
    const payload: unknown = JSON.parse(await blob.text());
    if (!isReport(payload) || payload.report_id !== report.report_id) return null;
    return blob;
  } catch {
    return null;
  }
}

/** Discover changes between two video versions without revision notes. */
export async function discoverChanges(
  preFinal: File,
  final: File,
  signal?: AbortSignal,
): Promise<DiscoverReport> {
  const body = new FormData();
  body.append("pre_final", preFinal);
  body.append("final", final);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}/discover`, { method: "POST", body, signal });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError(OFFLINE_HINT, true);
  }

  let payload: unknown = null;
  try {
    payload = await res.json();
  } catch {
    payload = null;
  }

  if (!res.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? String((payload as { detail: unknown }).detail)
        : `Discovery failed (HTTP ${res.status}).`;
    throw new ApiError(detail);
  }

  if (!isDiscoverReport(payload)) {
    throw new ApiError("The API responded, but the change report was not in the expected format.");
  }
  return payload;
}

/** Download the persisted Discover JSON report. */
export async function fetchDiscoverExport(report: DiscoverReport): Promise<Blob | null> {
  try {
    const res = await fetch(`${API_BASE}/discover/${encodeURIComponent(report.report_id)}/export`, {
      cache: "no-store",
    });
    if (!res.ok || !res.headers.get("content-type")?.includes("application/json")) return null;
    const blob = await res.blob();
    const payload: unknown = JSON.parse(await blob.text());
    if (!isDiscoverReport(payload) || payload.report_id !== report.report_id) return null;
    return blob;
  } catch {
    return null;
  }
}
