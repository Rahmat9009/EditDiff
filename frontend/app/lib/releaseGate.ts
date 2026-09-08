/**
 * Types and runtime validation for the Release Gate contract.
 *
 *   POST /release-gate            multipart: pre_final, final, notes
 *   GET  /release-gate/{id}
 *   GET  /release-gate/{id}/export
 *
 * These mirror backend/app/models.py exactly:
 *   ReleaseDecision, ChangeDisposition, TechnicalCheckStatus,
 *   TechnicalCheckSeverity, TechnicalCheck, ReleaseChangeAssessment,
 *   ReleaseGateSummary, ReleaseGateResult.
 *
 * The backend is the source of truth. Every field the backend declares is
 * required here and validated; nothing is optional "just in case".
 */

import {
  isDiscoverChange,
  isEvidence,
  isVerifyResult,
  type DetectedChange,
  type Evidence,
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

/** backend: TechnicalCheck */
export type TechnicalCheck = {
  id: string;
  label: string;
  status: TechnicalCheckStatus;
  severity: TechnicalCheckSeverity;
  confidence: number;
  explanation: string;
  evidence: Evidence;
};

/** backend: ReleaseChangeAssessment — the detected change is nested, not flattened. */
export type ReleaseChangeAssessment = {
  change: DetectedChange;
  disposition: ChangeDisposition;
  matched_revision_ids: string[];
  explanation: string;
};

/** backend: ReleaseGateSummary */
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

/** backend: ReleaseGateResult */
export type ReleaseGateResult = {
  report_id: string;
  decision: ReleaseDecision;
  decision_reasons: string[];
  summary: ReleaseGateSummary;
  baseline_duration_seconds: number;
  candidate_duration_seconds: number;
  requested_revisions: Result[];
  change_assessments: ReleaseChangeAssessment[];
  technical_checks: TechnicalCheck[];
};

function isOneOf<T extends string>(value: unknown, allowed: readonly T[]): value is T {
  return typeof value === "string" && (allowed as readonly string[]).includes(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

export function isReleaseChangeAssessment(value: unknown): value is ReleaseChangeAssessment {
  if (!value || typeof value !== "object") return false;
  const c = value as Partial<ReleaseChangeAssessment>;
  return (
    isDiscoverChange(c.change) &&
    isOneOf(c.disposition, CHANGE_DISPOSITIONS) &&
    isStringArray(c.matched_revision_ids) &&
    typeof c.explanation === "string"
  );
}

export function isTechnicalCheck(value: unknown): value is TechnicalCheck {
  if (!value || typeof value !== "object") return false;
  const c = value as Partial<TechnicalCheck>;
  return (
    typeof c.id === "string" &&
    typeof c.label === "string" &&
    isOneOf(c.status, TECHNICAL_CHECK_STATUSES) &&
    isOneOf(c.severity, TECHNICAL_CHECK_SEVERITIES) &&
    typeof c.confidence === "number" &&
    typeof c.explanation === "string" &&
    isEvidence(c.evidence)
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
  if (!isStringArray(c.decision_reasons)) return false;
  if (!isReleaseGateSummary(c.summary)) return false;
  if (typeof c.baseline_duration_seconds !== "number") return false;
  if (typeof c.candidate_duration_seconds !== "number") return false;
  if (!Array.isArray(c.requested_revisions) || !c.requested_revisions.every(isVerifyResult)) {
    return false;
  }
  if (
    !Array.isArray(c.change_assessments) ||
    !c.change_assessments.every(isReleaseChangeAssessment)
  ) {
    return false;
  }
  if (!Array.isArray(c.technical_checks) || !c.technical_checks.every(isTechnicalCheck)) {
    return false;
  }
  return true;
}

/**
 * The timestamp a technical check points at, when it has one.
 *
 * backend/app/technical.py builds check evidence through `_metric_evidence`,
 * which records metrics and reason codes but no timestamp, so today every
 * check returns null here and is reported without a rail marker. Reading it
 * from the evidence keeps the UI correct if a later check does carry one.
 */
export function technicalCheckTimestamp(check: TechnicalCheck): number | null {
  return check.evidence.timestamp_seconds ?? null;
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
 * export is "safe", only what the evidence did and did not establish.
 */
export const DECISION_MEANING: Record<ReleaseDecision, string> = {
  READY_TO_PUBLISH:
    "No unresolved changes detected above current thresholds. Requested revisions are supported by evidence and no technical check is failing.",
  NEEDS_REVIEW:
    "Evidence is incomplete or ambiguous somewhere in this export. A human decision is required before publishing.",
  BLOCKED:
    "Evidence contradicts the release: a requested revision failed, or a blocking technical check failed.",
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

/** Changes the gate could not tie to a passing requested revision. */
export function isUnresolved(assessment: ReleaseChangeAssessment): boolean {
  return assessment.disposition !== "ACCOUNTED_FOR";
}
