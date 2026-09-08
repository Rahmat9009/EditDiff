from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .media import probe_media
from .models import (
    ChangeConfidence,
    ChangeKind,
    DiscoverResponse,
    Evidence,
    EvidenceMetric,
    TechnicalCheck,
    TechnicalCheckSeverity,
    TechnicalCheckStatus,
)


BLACK_MEAN_MAX = 12.0
BLACK_DARK_PIXEL_RATIO_MIN = 0.98
BLACK_SUSTAINED_SECONDS = 1.0
AUDIO_ACTIVE_MIN = 0.008
AUDIO_SILENT_MAX = 0.004
AUDIO_DROPOUT_RATIO_MAX = 0.25
AUDIO_DROPOUT_SUSTAINED_SECONDS = 3.0


def _video_stream(probe: dict) -> dict:
    return next(stream for stream in probe["streams"] if stream.get("codec_type") == "video")


def _audio_streams(probe: dict) -> list[dict]:
    return [stream for stream in probe["streams"] if stream.get("codec_type") == "audio"]


def _metric_evidence(explanation: str, metrics: list[EvidenceMetric], methods: list[str],
                     reason_codes: list[str], thresholds: dict[str, float] | None = None) -> Evidence:
    return Evidence(explanation=explanation, metrics=metrics, methods=methods,
                    reason_codes=reason_codes, thresholds=thresholds or {})


def _resolution_check(pre_probe: dict, final_probe: dict) -> TechnicalCheck:
    before, after = _video_stream(pre_probe), _video_stream(final_probe)
    w1, h1 = int(before["width"]), int(before["height"])
    w2, h2 = int(after["width"]), int(after["height"])
    aspect1, aspect2 = w1 / h1, w2 / h2
    matches = (w1, h1) == (w2, h2)
    status = TechnicalCheckStatus.PASS if matches else TechnicalCheckStatus.REVIEW
    explanation = (
        "Resolution and aspect ratio are consistent between exports."
        if matches else
        "Resolution or aspect ratio changed; no delivery specification was supplied, so this requires review."
    )
    return TechnicalCheck(
        id="resolution-aspect-ratio", label="Resolution and aspect-ratio consistency",
        status=status, severity=TechnicalCheckSeverity.ADVISORY,
        confidence=0.99 if matches else 0.98, explanation=explanation,
        evidence=_metric_evidence(explanation, [
            EvidenceMetric(name="resolution", v1=f"{w1}x{h1}", v2=f"{w2}x{h2}"),
            EvidenceMetric(name="aspect_ratio", v1=round(aspect1, 5), v2=round(aspect2, 5),
                           delta=round(aspect2 - aspect1, 5), unit="ratio"),
        ], ["ffprobe_stream_metadata"], ["resolution_consistent" if matches else "resolution_or_aspect_changed"]),
    )


def _duration_check(baseline_duration: float, candidate_duration: float) -> TechnicalCheck:
    delta = candidate_duration - baseline_duration
    unusual_threshold = max(1.0, baseline_duration * 0.05)
    unusual = abs(delta) > unusual_threshold
    status = TechnicalCheckStatus.REVIEW if unusual else TechnicalCheckStatus.PASS
    explanation = (
        "Duration difference is within the conservative review threshold."
        if not unusual else
        "The export duration changed unusually; without a delivery specification this requires review."
    )
    return TechnicalCheck(
        id="duration-difference", label="Unusual duration difference", status=status,
        severity=TechnicalCheckSeverity.ADVISORY, confidence=0.99, explanation=explanation,
        evidence=_metric_evidence(explanation, [
            EvidenceMetric(name="duration_seconds", v1=round(baseline_duration, 3),
                           v2=round(candidate_duration, 3), delta=round(delta, 3), unit="seconds"),
        ], ["ffprobe_duration"], ["duration_within_review_threshold" if not unusual else "unusual_duration_difference"],
           {"review_delta_seconds": round(unusual_threshold, 3)}),
    )


def _black_flags(path: Path, duration: float, step: float = 0.25) -> list[bool]:
    cap = cv2.VideoCapture(str(path))
    flags: list[bool] = []
    try:
        for timestamp in np.arange(0.0, max(duration - 0.05, 0.0), step):
            cap.set(cv2.CAP_PROP_POS_MSEC, float(timestamp) * 1000)
            ok, frame = cap.read()
            if not ok or frame is None:
                flags.append(False)
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            flags.append(float(np.mean(gray)) <= BLACK_MEAN_MAX and float(np.mean(gray <= 20)) >= BLACK_DARK_PIXEL_RATIO_MIN)
    finally:
        cap.release()
    return flags


def _longest_run(flags: list[bool], step: float) -> float:
    longest = current = 0
    for flag in flags:
        current = current + 1 if flag else 0
        longest = max(longest, current)
    return longest * step


def _black_frame_check(pre_final: Path, final: Path, baseline_duration: float,
                       candidate_duration: float) -> TechnicalCheck:
    step = 0.25
    common_duration = min(baseline_duration, candidate_duration)
    baseline = _black_flags(pre_final, common_duration, step)
    candidate = _black_flags(final, common_duration, step)
    regression = [after and not before for before, after in zip(baseline, candidate)]
    sustained = _longest_run(regression, step)
    failed = sustained >= BLACK_SUSTAINED_SECONDS
    status = TechnicalCheckStatus.FAIL if failed else TechnicalCheckStatus.PASS
    explanation = (
        f"A {sustained:.2f}-second sustained black-frame regression was detected against non-black baseline footage."
        if failed else "No sustained black-frame regression was detected against non-black baseline footage."
    )
    return TechnicalCheck(
        id="black-frame-regression", label="Sustained black-frame regression", status=status,
        severity=TechnicalCheckSeverity.BLOCKING, confidence=0.99 if failed else 0.95,
        explanation=explanation,
        evidence=_metric_evidence(explanation, [
            EvidenceMetric(name="longest_black_regression", v2=round(sustained, 3), unit="seconds"),
        ], ["aligned_luma_sampling"], ["sustained_black_regression" if failed else "no_sustained_black_regression"],
           {"black_mean_max": BLACK_MEAN_MAX, "dark_pixel_ratio_min": BLACK_DARK_PIXEL_RATIO_MIN,
            "sustained_seconds": BLACK_SUSTAINED_SECONDS}),
    )


def _audio_track_check(pre_probe: dict, final_probe: dict) -> TechnicalCheck:
    before_count, after_count = len(_audio_streams(pre_probe)), len(_audio_streams(final_probe))
    if before_count == 0:
        status, severity, confidence, code = (
            TechnicalCheckStatus.NOT_APPLICABLE, TechnicalCheckSeverity.BLOCKING, 0.99, "baseline_has_no_audio_track"
        )
        explanation = "The baseline has no audio track, so complete audio-track loss is not applicable."
    elif after_count == 0:
        status, severity, confidence, code = (
            TechnicalCheckStatus.FAIL, TechnicalCheckSeverity.BLOCKING, 1.0, "complete_audio_track_loss"
        )
        explanation = "The baseline has audio, but the final export has no audio track."
    else:
        status, severity, confidence, code = (
            TechnicalCheckStatus.PASS, TechnicalCheckSeverity.BLOCKING, 1.0, "audio_track_present"
        )
        explanation = "The final export retains an audio track."
    return TechnicalCheck(
        id="complete-audio-track-loss", label="Complete audio-track loss", status=status,
        severity=severity, confidence=confidence, explanation=explanation,
        evidence=_metric_evidence(explanation, [
            EvidenceMetric(name="audio_track_count", v1=before_count, v2=after_count,
                           delta=float(after_count - before_count), unit="tracks"),
        ], ["ffprobe_stream_metadata"], [code]),
    )


def _audio_dropout_check(pre_probe: dict, final_probe: dict, discovery: DiscoverResponse,
                         accounted_change_ids: set[str]) -> TechnicalCheck:
    if not _audio_streams(pre_probe) or not _audio_streams(final_probe):
        explanation = "Aligned audio dropout analysis requires audio tracks in both exports."
        return TechnicalCheck(
            id="major-audio-dropout", label="Sustained major audio dropout",
            status=TechnicalCheckStatus.NOT_APPLICABLE, severity=TechnicalCheckSeverity.BLOCKING,
            confidence=0.99, explanation=explanation,
            evidence=_metric_evidence(explanation, [], ["aligned_audio_rms_envelope"], ["audio_tracks_required"]),
        )
    dropout_windows: list[float] = []
    for change in discovery.changes:
        if (
            change.id not in accounted_change_ids
            and change.kind == ChangeKind.AUDIO
            and change.confidence == ChangeConfidence.HIGH
            and "local_audio_muted" in change.evidence.reason_codes
        ):
            starts = [change.evidence.window_start_pre_final, change.evidence.window_start_final]
            ends = [change.evidence.window_end_pre_final, change.evidence.window_end_final]
            durations = [
                float(end) - float(start) for start, end in zip(starts, ends)
                if start is not None and end is not None
            ]
            dropout_windows.append(max(durations, default=0.0))
    sustained = max(dropout_windows, default=0.0)
    failed = sustained >= AUDIO_DROPOUT_SUSTAINED_SECONDS
    status = TechnicalCheckStatus.FAIL if failed else TechnicalCheckStatus.PASS
    explanation = (
        f"A {sustained:.2f}-second sustained major audio dropout was detected in aligned footage."
        if failed else "No sustained major audio dropout was detected in aligned footage."
    )
    return TechnicalCheck(
        id="major-audio-dropout", label="Sustained major audio dropout", status=status,
        severity=TechnicalCheckSeverity.BLOCKING, confidence=0.98 if failed else 0.94,
        explanation=explanation,
        evidence=_metric_evidence(explanation, [
            EvidenceMetric(name="longest_major_dropout", v2=round(sustained, 3), unit="seconds"),
        ], ["discover_bounded_sequence_alignment", "local_audio_rms_envelope"],
           ["sustained_major_audio_dropout" if failed else "no_sustained_major_audio_dropout"],
           {"source_active_min": AUDIO_ACTIVE_MIN, "candidate_silent_max": AUDIO_SILENT_MAX,
            "dropout_ratio_max": AUDIO_DROPOUT_RATIO_MAX,
            "sustained_seconds": AUDIO_DROPOUT_SUSTAINED_SECONDS}),
    )


def run_technical_checks(pre_final: Path, final: Path, discovery: DiscoverResponse,
                         accounted_change_ids: set[str] | None = None) -> list[TechnicalCheck]:
    """Run only the conservative first-version release checks against one media pair."""
    pre_probe, final_probe = probe_media(pre_final), probe_media(final)
    baseline_duration = discovery.pre_final_duration_seconds
    candidate_duration = discovery.final_duration_seconds
    return [
        _resolution_check(pre_probe, final_probe),
        _duration_check(baseline_duration, candidate_duration),
        _black_frame_check(pre_final, final, baseline_duration, candidate_duration),
        _audio_track_check(pre_probe, final_probe),
        _audio_dropout_check(pre_probe, final_probe, discovery, accounted_change_ids or set()),
    ]
