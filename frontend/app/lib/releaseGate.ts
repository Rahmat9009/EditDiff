/**
 * Types and runtime validation for the frozen Release Gate contract.
 *
 *   POST /release-gate            multipart: pre_final, final, notes
 *   GET  /release-gate/{id}
 *   GET  /release-gate/{id}/export
 *
 * The enumerations and the `ReleaseGateResult` / `ReleaseGateSummary` field
 * lists below are frozen and validated strictly.
 *
 * The element shapes inside `requested_revisions`, `change_assessments` and
 * `technical_checks` are modelled on the shapes EditDiff already ships:
 *   - a requested revision is a Verify `Result` (request + verdict + evidence)
 *   - a change assessment is a Discover `DetectedChange` plus a disposition
 *   - a technical check is an id / label / status / severity record
 * Everything beyond the minimum a row needs to render is optional, so a
 * richer backend response shows more detail instead of failing validation.
 */

import {
  isDiscoverChange,
  isVerifyResult,
  type DetectedChange,
  type Metric,
  type Result,
} from "./types";

export type ReleaseDecision = "READY_TO_PUBLISH" | "NEEDS_REVIEW" | "BLOCKED";

export const RELEASE_DECISIONS: ReleaseDecision[] = [
  "READY_TO_PUBLISH",
  "NEEDS_REVIEW",
  "BLOCKED",
];

export type ChangeDisposition = "ACCOUNTED_FOR" | "UNEXPECTED" | "REVIEW";

export const CHANGE_DISPOSITIONS: ChangeDisposition[] = [
  "ACCOUNTED_FOR",
  "UNEXPECTED",
  "REVIEW",
];

export type TechnicalCheckStatus = "PASS" | "FAIL" | "REVIEW" | "NOT_APPLICABLE";

export const TECHNICAL_CHECK_STATUSES: TechnicalCheckStatus[] = [
  "PASS",
  "FAIL",
  "REVIEW",
  "NOT_APPLICABLE",
];

export type TechnicalCheckSeverity = "ADVISORY" | "BLOCKING";

export const TECHNICAL_CHECK_SEVERITIES: TechnicalCheckSeverity[] = ["ADVISORY", "BLOCKING"];

export type ReleaseGateSummary = {
  requested_total: number;
  requested_passed: number;
  requested_failed: number;
  requested_review: number;
  accounted_changes: number;
  unexpected_changes: number;
  change_association_review: number;
  technical_passed: number;
  technical_failed: number;
  technical_review: number;
};

export const RELEASE_GATE_SUMMARY_FIELDS: (keyof ReleaseGateSummary)[] = [
  "requested_total",
  "requested_passed",
  "requested_failed",
  "requested_review",
  "accounted_changes",
  "unexpected_changes",
  "change_association_review",
  "technical_passed",
  "technical_failed",
  "technical_review",
];

/** A detected change plus the gate's judgement of whether it was asked for. */
export type ChangeAssessment = DetectedChange & {
  disposition: ChangeDisposition;
  /** Set when the change was matched to one of the requested revisions. */
  associated_revision_id?: string | null;
  association_rationale?: string | null;
};

export type TechnicalCheck = {
  id: string;
  name: string;
  status: TechnicalCheckStatus;
  severity: TechnicalCheckSeverity;
  detail?: string | null;
  explanation?: string | null;
  expected?: string | null;
  observed?: string | null;
  timestamp_seconds?: number | null;
  metrics?: Metric[];
  reason_codes?: string[];
};

export type ReleaseGateResult = {
  report_id: string;
  decision: ReleaseDecision;
  decision_reasons: string[];
  summary: ReleaseGateSummary;
  baseline_duration_seconds: number;
  candidate_duration_seconds: number;
  requested_revisions: Result[];
  change_assessments: ChangeAssessment[];
  technical_checks: TechnicalCheck[];
};

function isOneOf<T extends string>(value: unknown, allowed: readonly T[]): value is T {
  return typeof value === "string" && (allowed as readonly string[]).includes(value);
}

export function isChangeAssessment(value: unknown): value is ChangeAssessment {
  if (!isDiscoverChange(value)) return false;
  return isOneOf((value as ChangeAssessment).disposition, CHANGE_DISPOSITIONS);
}

export function isTechnicalCheck(value: unknown): value is TechnicalCheck {
  if (!value || typeof value !== "object") return false;
  const c = value as Partial<TechnicalCheck>;
  return (
    typeof c.id === "string" &&
    typeof c.name === "string" &&
    isOneOf(c.status, TECHNICAL_CHECK_STATUSES) &&
    isOneOf(c.severity, TECHNICAL_CHECK_SEVERITIES)
  );
}

export function isReleaseGateSummary(value: unknown): value is ReleaseGateSummary {
  if (!value || typeof value !== "object") return false;
  const summary = value as Record<string, unknown>;
  return RELEASE_GATE_SUMMARY_FIELDS.every((field) => typeof summary[field] === "number");
}

/** Runtime guard: a malformed or non-EditDiff response must not crash the UI. */
export function isReleaseGateResult(value: unknown): value is ReleaseGateResult {
  if (!value || typeof value !== "object") return false;
  const c = value as Partial<ReleaseGateResult>;
  if (typeof c.report_id !== "string") return false;
  if (!isOneOf(c.decision, RELEASE_DECISIONS)) return false;
  if (!Array.isArray(c.decision_reasons)) return false;
  if (!c.decision_reasons.every((r) => typeof r === "string")) return false;
  if (!isReleaseGateSummary(c.summary)) return false;
  if (typeof c.baseline_duration_seconds !== "number") return false;
  if (typeof c.candidate_duration_seconds !== "number") return false;
  if (!Array.isArray(c.requested_revisions) || !c.requested_revisions.every(isVerifyResult)) {
    return false;
  }
  if (!Array.isArray(c.change_assessments) || !c.change_assessments.every(isChangeAssessment)) {
    return false;
  }
  if (!Array.isArray(c.technical_checks) || !c.technical_checks.every(isTechnicalCheck)) {
    return false;
  }
  return true;
}

/** Non-colour cue: decisions never rely on hue alone. */
export const DECISION_GLYPH: Record<ReleaseDecision, string> = {
  READY_TO_PUBLISH: "✓",
  NEEDS_REVIEW: "?",
  BLOCKED: "✕",
};

export const DECISION_LABEL: Record<ReleaseDecision, string> = {
  READY_TO_PUBLISH: "READY TO PUBLISH",
  NEEDS_REVIEW: "NEEDS REVIEW",
  BLOCKED: "BLOCKED",
};

/**
 * Release Gate reports evidence, not omniscience: never tell an operator the
 * export is "safe", only what was and was not detected at current thresholds.
 */
export const DECISION_MEANING: Record<ReleaseDecision, string> = {
  READY_TO_PUBLISH:
    "No unresolved changes detected above current thresholds. Requested revisions are supported by evidence and no technical check is failing.",
  NEEDS_REVIEW:
    "Evidence is incomplete or ambiguous somewhere in this export. A human decision is required before publishing.",
  BLOCKED:
    "Evidence contradicts the release: at least one requested revision did not land, an unexpected change was detected, or a blocking technical check failed.",
};

export const DISPOSITION_LABEL: Record<ChangeDisposition, string> = {
  ACCOUNTED_FOR: "ACCOUNTED FOR",
  UNEXPECTED: "UNEXPECTED",
  REVIEW: "REVIEW",
};

export const DISPOSITION_GLYPH: Record<ChangeDisposition, string> = {
  ACCOUNTED_FOR: "✓",
  UNEXPECTED: "!",
  REVIEW: "?",
};

export const DISPOSITION_MEANING: Record<ChangeDisposition, string> = {
  ACCOUNTED_FOR: "This change matches a requested revision.",
  UNEXPECTED: "This change was detected but was not requested in the notes.",
  REVIEW: "EditDiff could not associate this change with a requested revision.",
};

export const TECHNICAL_STATUS_GLYPH: Record<TechnicalCheckStatus, string> = {
  PASS: "✓",
  FAIL: "✕",
  REVIEW: "?",
  NOT_APPLICABLE: "–",
};

export const TECHNICAL_STATUS_LABEL: Record<TechnicalCheckStatus, string> = {
  PASS: "PASS",
  FAIL: "FAIL",
  REVIEW: "REVIEW",
  NOT_APPLICABLE: "N/A",
};

export function technicalCheckDetail(check: TechnicalCheck): string {
  return check.detail ?? check.explanation ?? "";
}
