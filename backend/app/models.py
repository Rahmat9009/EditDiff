from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class CheckKind(str, Enum):
    MUTE_AUDIO = "mute_audio"
    VISUAL_CHANGE = "visual_change"
    REMOVE_PAUSE = "remove_pause"
    TEXT_CHANGE = "text_change"
    ZOOM_CROP = "zoom_crop"
    GENERIC = "generic"


class RevisionRequest(BaseModel):
    id: str
    raw_text: str
    kind: CheckKind = CheckKind.GENERIC
    timestamp_seconds: float | None = None
    window_seconds: float = Field(default=2.0, ge=0.25, le=10.0)
    expected: str | None = None
    expected_old_text: str | None = None
    expected_new_text: str | None = None


class EvidenceMetric(BaseModel):
    name: str
    v1: float | str | None = None
    v2: float | str | None = None
    delta: float | None = None
    unit: str | None = None


class EvidenceFrame(BaseModel):
    version: str
    timestamp_seconds: float
    path: str


class Evidence(BaseModel):
    timestamp_seconds: float | None = None
    v1_frame_path: str | None = None
    v2_frame_path: str | None = None
    metrics: list[EvidenceMetric] = Field(default_factory=list)
    explanation: str
    methods: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    thresholds: dict[str, float] = Field(default_factory=dict)
    window_start_seconds: float | None = None
    window_end_seconds: float | None = None
    frames: list[EvidenceFrame] = Field(default_factory=list)
    semantic_status: str = "not_requested"
    signal_agreement: str = "insufficient"
    before_observation: str | None = None
    after_observation: str | None = None
    semantic_confidence: float | None = Field(default=None, ge=0, le=1)
    semantic_supporting_frame_indices: list[int] = Field(default_factory=list)
    observed_after_text: str | None = None


class VerificationResult(BaseModel):
    request: RevisionRequest
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    evidence: Evidence


class AnalyzeResponse(BaseModel):
    report_id: str
    summary: dict[str, int]
    results: list[VerificationResult]


class ChangeKind(str, Enum):
    VISUAL = "VISUAL"
    TIMING = "TIMING"
    AUDIO = "AUDIO"
    TEXT = "TEXT"
    REVIEW = "REVIEW"


class ChangeConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


TextSemanticStatus = Literal[
    "not_configured",
    "attempted",
    "classified_text",
    "same_text",
    "unreadable",
    "low_confidence",
    "invalid_response",
    "api_error",
    "timeout",
    "call_limit_reached",
]


class ChangeEvidence(BaseModel):
    pre_final_timestamp_seconds: float | None = None
    final_timestamp_seconds: float | None = None
    window_start_pre_final: float | None = None
    window_end_pre_final: float | None = None
    window_start_final: float | None = None
    window_end_final: float | None = None
    pre_final_frame_path: str | None = None
    final_frame_path: str | None = None
    metrics: list[EvidenceMetric] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    text_semantic_status: TextSemanticStatus | None = None
    text_before: str | None = None
    text_after: str | None = None
    explanation: str


class DetectedChange(BaseModel):
    id: str
    kind: ChangeKind
    confidence: ChangeConfidence
    title: str
    description: str
    evidence: ChangeEvidence


class DiscoverSummary(BaseModel):
    total_changes: int
    visual: int
    timing: int
    audio: int
    text: int
    review: int


class DiscoverResponse(BaseModel):
    report_id: str
    pre_final_duration_seconds: float
    final_duration_seconds: float
    duration_delta_seconds: float
    summary: DiscoverSummary
    changes: list[DetectedChange]


class ReleaseDecision(str, Enum):
    READY_TO_PUBLISH = "READY_TO_PUBLISH"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    BLOCKED = "BLOCKED"


class ChangeDisposition(str, Enum):
    ACCOUNTED_FOR = "ACCOUNTED_FOR"
    UNEXPECTED = "UNEXPECTED"
    REVIEW = "REVIEW"


class TechnicalCheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class TechnicalCheckSeverity(str, Enum):
    ADVISORY = "ADVISORY"
    BLOCKING = "BLOCKING"


class TechnicalCheck(BaseModel):
    id: str
    label: str
    status: TechnicalCheckStatus
    severity: TechnicalCheckSeverity
    confidence: float = Field(ge=0, le=1)
    explanation: str
    evidence: Evidence


class ReleaseChangeAssessment(BaseModel):
    change: DetectedChange
    disposition: ChangeDisposition
    matched_revision_ids: list[str] = Field(default_factory=list)
    explanation: str


class ReleaseGateSummary(BaseModel):
    requested_total: int
    requested_passed: int
    requested_failed: int
    requested_review: int
    accounted_changes: int
    unexpected_changes: int
    change_association_review: int
    technical_passed: int
    technical_failed: int
    technical_review: int


class ReleaseGateResult(BaseModel):
    report_id: str
    decision: ReleaseDecision
    decision_reasons: list[str] = Field(default_factory=list)
    summary: ReleaseGateSummary
    baseline_duration_seconds: float
    candidate_duration_seconds: float
    requested_revisions: list[VerificationResult]
    change_assessments: list[ReleaseChangeAssessment]
    technical_checks: list[TechnicalCheck]
