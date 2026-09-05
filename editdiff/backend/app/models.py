from __future__ import annotations

from enum import Enum
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


class EvidenceMetric(BaseModel):
    name: str
    v1: float | str | None = None
    v2: float | str | None = None
    delta: float | None = None
    unit: str | None = None


class Evidence(BaseModel):
    timestamp_seconds: float | None = None
    v1_frame_path: str | None = None
    v2_frame_path: str | None = None
    metrics: list[EvidenceMetric] = []
    explanation: str


class VerificationResult(BaseModel):
    request: RevisionRequest
    verdict: Verdict
    confidence: float = Field(ge=0, le=1)
    evidence: Evidence


class AnalyzeResponse(BaseModel):
    report_id: str
    summary: dict[str, int]
    results: list[VerificationResult]
