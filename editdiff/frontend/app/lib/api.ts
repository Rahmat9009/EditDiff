import { isReport, type Report } from "./types";

/** Public base URL of the EditDiff API. Never put secrets in NEXT_PUBLIC_*. */
export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

/** Absolute URL for an evidence asset returned as an API-relative path. */
export function assetUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
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

/**
 * Optional audit export. The backend endpoint may not exist yet, so callers
 * must be ready for `null` and fall back to a client-side export.
 */
export async function fetchAuditExport(report: Report): Promise<Blob | null> {
  const candidates = [report.export_url, `/reports/${report.report_id}/export`].filter(
    Boolean,
  ) as string[];
  for (const candidate of candidates) {
    try {
      const res = await fetch(assetUrl(candidate) as string, { cache: "no-store" });
      if (res.ok) return await res.blob();
    } catch {
      /* endpoint unavailable — fall through to the client-side export */
    }
  }
  return null;
}
