/**
 * Types for the frozen POST /analyze contract.
 *
 * Required fields mirror backend/app/models.py. Everything the backend may add
 * later (semantic verification, export links, media metadata) is typed as
 * optional so a richer response renders extra detail without breaking the app.
 */

export type Verdict = "PASS" | "FAIL" | "REVIEW";

export const VERDICTS: Verdict[] = ["PASS", "FAIL", "REVIEW"];

export type CheckKind =
  | "mute_audio"
  | "visual_change"
  | "remove_pause"
  | "text_change"
  | "zoom_crop"
  | "generic"
  | (string & {});

export type Metric = {
  name: string;
  v1?: number | string | null;
  v2?: number | string | null;
  delta?: number | null;
  unit?: string | null;
};

export type RevisionRequest = {
  id: string;
  raw_text: string;
  kind: CheckKind;
  timestamp_seconds?: number | null;
  window_seconds?: number | null;
  expected?: string | null;
  expected_old_text?: string | null;
  expected_new_text?: string | null;
};

/** Optional semantic layer. Shape is intentionally permissive. */
export type SemanticEvidence = {
  model?: string | null;
  verdict?: string | null;
  confidence?: number | null;
  rationale?: string | null;
  explanation?: string | null;
  expected?: string | null;
  observed?: string | null;
  v1_text?: string | null;
  v2_text?: string | null;
  [key: string]: unknown;
};

export type Evidence = {
  timestamp_seconds?: number | null;
  v1_frame_path?: string | null;
  v2_frame_path?: string | null;
  metrics: Metric[];
  explanation: string;
  methods?: string[];
  window_start_seconds?: number | null;
  window_end_seconds?: number | null;
  reason_codes?: string[];
  semantic_status?: string;
  signal_agreement?: string;
  thresholds?: Record<string, number>;
  frames?: { version: string; timestamp_seconds: number; path: string }[];
  before_observation?: string | null;
  after_observation?: string | null;
  observed_after_text?: string | null;
  semantic_confidence?: number | null;
  semantic_supporting_frame_indices?: number[];
  /** Legacy optional shapes remain accepted. */
  semantic?: SemanticEvidence | null;
  semantic_result?: SemanticEvidence | null;
  semantic_evidence?: SemanticEvidence | null;
};

export type Result = {
  request: RevisionRequest;
  verdict: Verdict;
  confidence: number;
  evidence: Evidence;
};

export type Report = {
  report_id: string;
  summary: Record<string, number>;
  results: Result[];
  /** Optional future fields. */
  generated_at?: string | null;
  export_url?: string | null;
};

/** Runtime guard: a malformed or non-EditDiff response must not crash the UI. */
export function isReport(value: unknown): value is Report {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<Report>;
  if (typeof candidate.report_id !== "string") return false;
  if (!candidate.summary || typeof candidate.summary !== "object") return false;
  if (!Array.isArray(candidate.results)) return false;
  return candidate.results.every(
    (r) =>
      r &&
      typeof r === "object" &&
      typeof r.verdict === "string" &&
      typeof r.confidence === "number" &&
      !!r.request &&
      typeof r.request.raw_text === "string" &&
      !!r.evidence &&
      typeof r.evidence.explanation === "string",
  );
}

export function semanticOf(evidence: Evidence): SemanticEvidence | null {
  const raw = evidence.semantic ?? evidence.semantic_result ?? evidence.semantic_evidence;
  if (!raw || typeof raw !== "object") return null;
  const hasContent = Object.values(raw).some((v) => v !== null && v !== undefined && v !== "");
  return hasContent ? raw : null;
}

/* --------------------------------------------------------------------------
   Discover Changes Types (Workflow 2)
   -------------------------------------------------------------------------- */

export type ChangeKind = "VISUAL" | "TIMING" | "AUDIO" | "TEXT" | "REVIEW";

export const CHANGE_KINDS: ChangeKind[] = ["VISUAL", "TIMING", "AUDIO", "TEXT", "REVIEW"];

export type ChangeConfidence = "HIGH" | "MEDIUM" | "LOW";

export type ChangeEvidence = {
  pre_final_timestamp_seconds?: number | null;
  final_timestamp_seconds?: number | null;
  window_start_pre_final?: number | null;
  window_end_pre_final?: number | null;
  window_start_final?: number | null;
  window_end_final?: number | null;
  pre_final_frame_path?: string | null;
  final_frame_path?: string | null;
  metrics: Metric[];
  methods?: string[];
  reason_codes?: string[];
  explanation: string;
};

export type DetectedChange = {
  id: string;
  kind: ChangeKind;
  confidence: ChangeConfidence;
  title: string;
  description: string;
  evidence: ChangeEvidence;
};

export type DiscoverSummary = {
  total_changes: number;
  visual: number;
  timing: number;
  audio: number;
  text: number;
  review: number;
};

export type DiscoverReport = {
  report_id: string;
  pre_final_duration_seconds: number;
  final_duration_seconds: number;
  duration_delta_seconds: number;
  summary: DiscoverSummary;
  changes: DetectedChange[];
  generated_at?: string | null;
  export_url?: string | null;
};

/** Runtime guard: a malformed Discover API response must not crash the UI. */
export function isDiscoverReport(value: unknown): value is DiscoverReport {
  if (!value || typeof value !== "object") return false;
  const c = value as Partial<DiscoverReport>;
  if (typeof c.report_id !== "string") return false;
  if (typeof c.pre_final_duration_seconds !== "number") return false;
  if (typeof c.final_duration_seconds !== "number") return false;
  if (typeof c.duration_delta_seconds !== "number") return false;
  if (!c.summary || typeof c.summary !== "object") return false;
  if (typeof c.summary.total_changes !== "number") return false;
  if (!Array.isArray(c.changes)) return false;
  return c.changes.every(
    (ch) =>
      ch &&
      typeof ch === "object" &&
      typeof ch.id === "string" &&
      typeof ch.kind === "string" &&
      typeof ch.confidence === "string" &&
      typeof ch.title === "string" &&
      typeof ch.description === "string" &&
      !!ch.evidence &&
      typeof ch.evidence.explanation === "string" &&
      Array.isArray(ch.evidence.metrics),
  );
}
