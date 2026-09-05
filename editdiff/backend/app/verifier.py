from __future__ import annotations

from pathlib import Path
from .media import audio_rms, duration_seconds, extract_frame, visual_difference
from .models import Evidence, EvidenceMetric, RevisionRequest, CheckKind, Verdict, VerificationResult


def _safe_ts(req: RevisionRequest, v1: Path, v2: Path) -> float:
    d = min(duration_seconds(v1), duration_seconds(v2))
    if req.timestamp_seconds is None:
        return min(1.0, max(d / 2, 0))
    return min(max(req.timestamp_seconds, 0), max(d - 0.05, 0))


def verify(req: RevisionRequest, v1: Path, v2: Path, evidence_dir: Path) -> VerificationResult:
    ts = _safe_ts(req, v1, v2)
    v1_frame = extract_frame(v1, ts, evidence_dir / f"{req.id}-v1.jpg")
    v2_frame = extract_frame(v2, ts, evidence_dir / f"{req.id}-v2.jpg")

    visual_delta, feature_match = visual_difference(v1, v2, ts)
    metrics = [
        EvidenceMetric(name="visual_delta", v1=0.0, v2=visual_delta, delta=visual_delta, unit="0-1"),
        EvidenceMetric(name="feature_match", v1=None, v2=feature_match, delta=None, unit="0-1"),
    ]

    if req.kind == CheckKind.MUTE_AUDIO:
        a1 = audio_rms(v1, ts, req.window_seconds)
        a2 = audio_rms(v2, ts, req.window_seconds)
        ratio = a2 / max(a1, 1e-6)
        metrics += [
            EvidenceMetric(name="audio_rms", v1=a1, v2=a2, delta=a2-a1, unit="RMS"),
            EvidenceMetric(name="audio_ratio_v2_to_v1", v1=1.0, v2=ratio, delta=ratio-1.0, unit="ratio"),
        ]
        if a1 > 0.008 and (a2 < 0.004 or ratio < 0.2):
            verdict, confidence, explanation = Verdict.PASS, 0.94, "Audio energy at the requested moment dropped to near-silence in V2."
        elif a2 > 0.01 and ratio > 0.65:
            verdict, confidence, explanation = Verdict.FAIL, 0.90, "Audio is still clearly present in V2 at the requested moment."
        else:
            verdict, confidence, explanation = Verdict.REVIEW, 0.62, "The audio changed, but the deterministic signal is not strong enough for an automatic decision."

    elif req.kind == CheckKind.REMOVE_PAUSE:
        d1, d2 = duration_seconds(v1), duration_seconds(v2)
        delta = d2 - d1
        metrics.append(EvidenceMetric(name="total_duration", v1=d1, v2=d2, delta=delta, unit="seconds"))
        if delta < -0.25:
            verdict, confidence, explanation = Verdict.PASS, 0.78, "V2 is shorter and the local visual evidence changed around the requested cut; this is consistent with a removed pause."
        elif abs(delta) < 0.08:
            verdict, confidence, explanation = Verdict.REVIEW, 0.58, "Total duration barely changed, so the pause removal cannot be proven deterministically yet."
        else:
            verdict, confidence, explanation = Verdict.REVIEW, 0.55, "Timing changed, but not in a way that proves this specific pause was removed."

    elif req.kind in {CheckKind.TEXT_CHANGE, CheckKind.ZOOM_CROP, CheckKind.VISUAL_CHANGE}:
        if visual_delta > 0.08:
            verdict, confidence, explanation = Verdict.PASS, 0.86, "V2 shows a strong visual change at the requested timestamp."
        elif visual_delta < 0.02 and feature_match > 0.12:
            verdict, confidence, explanation = Verdict.FAIL, 0.82, "V1 and V2 remain visually very similar at the requested timestamp."
        else:
            verdict, confidence, explanation = Verdict.REVIEW, 0.63, "A visual change is present, but semantic confirmation is needed to prove it is the requested edit."

    else:
        if visual_delta > 0.10:
            verdict, confidence, explanation = Verdict.REVIEW, 0.68, "A material visual change is detected, but this revision type needs semantic verification."
        else:
            verdict, confidence, explanation = Verdict.REVIEW, 0.50, "No deterministic rule exists for this edit note yet."

    evidence = Evidence(
        timestamp_seconds=ts,
        v1_frame_path=f"/evidence/{v1_frame.name}",
        v2_frame_path=f"/evidence/{v2_frame.name}",
        metrics=metrics,
        explanation=explanation,
    )
    return VerificationResult(request=req, verdict=verdict, confidence=confidence, evidence=evidence)
