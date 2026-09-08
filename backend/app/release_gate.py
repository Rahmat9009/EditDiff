from __future__ import annotations

from pathlib import Path

from .discovery import discover_changes
from .models import (
    ChangeDisposition,
    ChangeKind,
    CheckKind,
    DetectedChange,
    ReleaseChangeAssessment,
    ReleaseDecision,
    ReleaseGateResult,
    ReleaseGateSummary,
    RevisionRequest,
    TechnicalCheck,
    TechnicalCheckSeverity,
    TechnicalCheckStatus,
    Verdict,
    VerificationResult,
)
from .technical import run_technical_checks
from .verifier import verify


COMPATIBLE_CHANGE_KINDS: dict[CheckKind, set[ChangeKind]] = {
    CheckKind.MUTE_AUDIO: {ChangeKind.AUDIO},
    CheckKind.REMOVE_PAUSE: {ChangeKind.TIMING},
    CheckKind.TEXT_CHANGE: {ChangeKind.TEXT},
    CheckKind.VISUAL_CHANGE: {ChangeKind.VISUAL},
    CheckKind.ZOOM_CROP: {ChangeKind.VISUAL},
    CheckKind.GENERIC: set(),
}


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _overlaps(change: DetectedChange, result: VerificationResult) -> bool:
    evidence = change.evidence
    start = evidence.window_start_pre_final
    end = evidence.window_end_pre_final
    if start is None:
        start = evidence.pre_final_timestamp_seconds
    if end is None:
        end = evidence.pre_final_timestamp_seconds
    request_start = result.evidence.window_start_seconds
    request_end = result.evidence.window_end_seconds
    if None in (start, end, request_start, request_end):
        return False
    return max(float(start), float(request_start)) <= min(float(end), float(request_end))


def _text_is_compatible(change: DetectedChange, result: VerificationResult) -> bool:
    request = result.request
    before, after = change.evidence.text_before, change.evidence.text_after
    semantic_text_exists = before is not None or after is not None
    if semantic_text_exists and request.expected_old_text is not None:
        if before is None or _normalize_text(before) != _normalize_text(request.expected_old_text):
            return False
    if semantic_text_exists and request.expected_new_text is not None:
        if after is None or _normalize_text(after) != _normalize_text(request.expected_new_text):
            return False
    return True


def correlate_changes(changes: list[DetectedChange], revisions: list[VerificationResult]
                      ) -> list[ReleaseChangeAssessment]:
    assessments: list[ReleaseChangeAssessment] = []
    for change in changes:
        if change.kind == ChangeKind.REVIEW:
            assessments.append(ReleaseChangeAssessment(
                change=change, disposition=ChangeDisposition.REVIEW,
                explanation="Discovery could not classify this change confidently; it remains visible for review.",
            ))
            continue
        matches = [
            revision for revision in revisions
            if change.kind in COMPATIBLE_CHANGE_KINDS[revision.request.kind]
            and _overlaps(change, revision)
        ]
        ids = [revision.request.id for revision in matches]
        if len(matches) == 0:
            assessments.append(ReleaseChangeAssessment(
                change=change, disposition=ChangeDisposition.UNEXPECTED, matched_revision_ids=[],
                explanation="No type-compatible requested-revision evidence window overlaps this change.",
            ))
        elif len(matches) > 1:
            assessments.append(ReleaseChangeAssessment(
                change=change, disposition=ChangeDisposition.REVIEW, matched_revision_ids=ids,
                explanation="This change overlaps more than one compatible requested revision; association is ambiguous.",
            ))
        elif matches[0].verdict != Verdict.PASS:
            assessments.append(ReleaseChangeAssessment(
                change=change, disposition=ChangeDisposition.REVIEW, matched_revision_ids=ids,
                explanation="The overlapping requested revision did not pass, so this change cannot be accounted for.",
            ))
        elif change.kind == ChangeKind.TEXT and not _text_is_compatible(change, matches[0]):
            assessments.append(ReleaseChangeAssessment(
                change=change, disposition=ChangeDisposition.REVIEW, matched_revision_ids=ids,
                explanation="Semantic before/after text does not exactly match the quoted request.",
            ))
        else:
            assessments.append(ReleaseChangeAssessment(
                change=change, disposition=ChangeDisposition.ACCOUNTED_FOR, matched_revision_ids=ids,
                explanation="Exactly one compatible passing revision evidence window overlaps this change.",
            ))
    # Multiple detected regions cannot all be confidently explained by one
    # requested revision. Preserve each one and expose the association ambiguity.
    change_ids_by_revision: dict[str, list[str]] = {}
    for assessment in assessments:
        if assessment.disposition == ChangeDisposition.ACCOUNTED_FOR:
            for revision_id in assessment.matched_revision_ids:
                change_ids_by_revision.setdefault(revision_id, []).append(assessment.change.id)
    ambiguous_revision_ids = {
        revision_id for revision_id, change_ids in change_ids_by_revision.items() if len(change_ids) > 1
    }
    if ambiguous_revision_ids:
        assessments = [
            assessment.model_copy(update={
                "disposition": ChangeDisposition.REVIEW,
                "explanation": "Multiple detected changes map to one requested revision; association is ambiguous.",
            })
            if ambiguous_revision_ids.intersection(assessment.matched_revision_ids)
            else assessment
            for assessment in assessments
        ]
    return assessments


def decide_release(revisions: list[VerificationResult], assessments: list[ReleaseChangeAssessment],
                   technical_checks: list[TechnicalCheck]) -> tuple[ReleaseDecision, list[str]]:
    blocking_reasons: list[str] = []
    review_reasons: list[str] = []
    failed_revisions = [item.request.id for item in revisions if item.verdict == Verdict.FAIL]
    if failed_revisions:
        blocking_reasons.append("Requested revisions failed: " + ", ".join(failed_revisions))
    blocking_checks = [
        item.label for item in technical_checks
        if item.severity == TechnicalCheckSeverity.BLOCKING and item.status == TechnicalCheckStatus.FAIL
    ]
    if blocking_checks:
        blocking_reasons.append("Blocking technical checks failed: " + ", ".join(blocking_checks))
    if blocking_reasons:
        return ReleaseDecision.BLOCKED, blocking_reasons

    review_revisions = [item.request.id for item in revisions if item.verdict == Verdict.REVIEW]
    if review_revisions:
        review_reasons.append("Requested revisions require review: " + ", ".join(review_revisions))
    unexpected = [item.change.id for item in assessments if item.disposition == ChangeDisposition.UNEXPECTED]
    if unexpected:
        review_reasons.append("Unexpected discovered changes: " + ", ".join(unexpected))
    association_review = [item.change.id for item in assessments if item.disposition == ChangeDisposition.REVIEW]
    if association_review:
        review_reasons.append("Change association or discovery requires review: " + ", ".join(association_review))
    technical_review = [item.label for item in technical_checks if item.status == TechnicalCheckStatus.REVIEW]
    if technical_review:
        review_reasons.append("Technical checks require review: " + ", ".join(technical_review))
    advisory_failures = [
        item.label for item in technical_checks
        if item.severity == TechnicalCheckSeverity.ADVISORY and item.status == TechnicalCheckStatus.FAIL
    ]
    if advisory_failures:
        review_reasons.append("Advisory technical checks failed: " + ", ".join(advisory_failures))
    if review_reasons:
        return ReleaseDecision.NEEDS_REVIEW, review_reasons
    return ReleaseDecision.READY_TO_PUBLISH, ["All requested revisions, discovered changes, and applicable technical checks passed."]


def build_summary(revisions: list[VerificationResult], assessments: list[ReleaseChangeAssessment],
                  technical_checks: list[TechnicalCheck]) -> ReleaseGateSummary:
    return ReleaseGateSummary(
        requested_total=len(revisions),
        requested_passed=sum(item.verdict == Verdict.PASS for item in revisions),
        requested_failed=sum(item.verdict == Verdict.FAIL for item in revisions),
        requested_review=sum(item.verdict == Verdict.REVIEW for item in revisions),
        accounted_changes=sum(item.disposition == ChangeDisposition.ACCOUNTED_FOR for item in assessments),
        unexpected_changes=sum(item.disposition == ChangeDisposition.UNEXPECTED for item in assessments),
        change_association_review=sum(item.disposition == ChangeDisposition.REVIEW for item in assessments),
        technical_passed=sum(item.status == TechnicalCheckStatus.PASS for item in technical_checks),
        technical_failed=sum(item.status == TechnicalCheckStatus.FAIL for item in technical_checks),
        technical_review=sum(item.status == TechnicalCheckStatus.REVIEW for item in technical_checks),
    )


def run_release_gate(requests: list[RevisionRequest], pre_final: Path, final: Path,
                     evidence_dir: Path) -> ReleaseGateResult:
    """Orchestrate Verify and Discover once over the same uploaded pair."""
    revisions = [verify(request, pre_final, final, evidence_dir) for request in requests]
    discovery = discover_changes(pre_final, final, evidence_dir)
    assessments = correlate_changes(discovery.changes, revisions)
    accounted_change_ids = {
        item.change.id for item in assessments if item.disposition == ChangeDisposition.ACCOUNTED_FOR
    }
    technical_checks = run_technical_checks(pre_final, final, discovery, accounted_change_ids)
    decision, reasons = decide_release(revisions, assessments, technical_checks)
    return ReleaseGateResult(
        report_id=evidence_dir.name,
        decision=decision,
        decision_reasons=reasons,
        summary=build_summary(revisions, assessments, technical_checks),
        baseline_duration_seconds=discovery.pre_final_duration_seconds,
        candidate_duration_seconds=discovery.final_duration_seconds,
        requested_revisions=revisions,
        change_assessments=assessments,
        technical_checks=technical_checks,
    )
