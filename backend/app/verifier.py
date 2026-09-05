from __future__ import annotations

from pathlib import Path
import re

from .media import audio_rms, duration_seconds, extract_frame, has_audio, visual_difference
from .models import Evidence, EvidenceFrame, EvidenceMetric, RevisionRequest, CheckKind, Verdict, VerificationResult
from .pause import THRESHOLDS as PAUSE_THRESHOLDS, check_pause
from .semantic import SemanticFinding, verify_semantic

VISUAL_THRESHOLDS = {"unchanged_max": 0.002, "changed_min": 0.004, "semantic_confidence_min": 0.75}
AUDIO_THRESHOLDS = {"source_active_min": 0.008, "muted_max": 0.004,
                    "mute_ratio_max": 0.2, "retained_min": 0.01, "retained_ratio_min": 0.65}


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def fuse_visual(req: RevisionRequest, deltas: list[float], semantic: SemanticFinding | None
                ) -> tuple[Verdict, float, str, str]:
    unchanged = max(deltas) < VISUAL_THRESHOLDS["unchanged_max"]
    if unchanged:
        if semantic and semantic.verdict == "PASS":
            return Verdict.REVIEW, 0.4, "semantic_conflicts_with_unchanged_frames", "disagreement"
        return Verdict.FAIL, 0.8, "no_visible_revision_in_window", "agreement" if semantic else "deterministic_only"
    if not semantic or semantic.confidence < VISUAL_THRESHOLDS["semantic_confidence_min"]:
        return Verdict.REVIEW, 0.45, "exact_intent_unconfirmed", "insufficient"
    if semantic.verdict == "REVIEW":
        return Verdict.REVIEW, 0.45, "semantic_ambiguous", "insufficient"
    if semantic.verdict == "PASS":
        if not semantic.after_state_confirmed or not any(
            deltas[i] >= VISUAL_THRESHOLDS["changed_min"] for i in semantic.supporting_frame_indices
        ):
            return Verdict.REVIEW, 0.4, "after_state_or_change_unconfirmed", "disagreement"
        if req.kind == CheckKind.TEXT_CHANGE and (
            not req.expected_new_text or not semantic.observed_after_text
            or _normalize(req.expected_new_text) != _normalize(semantic.observed_after_text)
        ):
            return Verdict.REVIEW, 0.4, "exact_after_text_unconfirmed", "disagreement"
        if req.kind == CheckKind.ZOOM_CROP and re.search(r"\d+(?:\.\d+)?\s*%", req.raw_text):
            return Verdict.REVIEW, 0.5, "exact_crop_percentage_unmeasured", "insufficient"
        return Verdict.PASS, min(semantic.confidence, 0.88), "requested_after_state_observed", "agreement"
    if semantic.after_state_confirmed:
        return Verdict.REVIEW, 0.4, "semantic_self_contradiction", "disagreement"
    return Verdict.FAIL, min(semantic.confidence, 0.82), "requested_after_state_contradicted", "semantic_only"


def check_mute(a1: float, a2: float) -> tuple[Verdict, float, str]:
    ratio = a2 / max(a1, 1e-6)
    if a1 > 0.008 and a2 < 0.004 and ratio < 0.2:
        return Verdict.PASS, 0.9, "local_audio_muted"
    if a2 > 0.01 and ratio > 0.65:
        return Verdict.FAIL, 0.86, "local_audio_retained"
    return Verdict.REVIEW, 0.45, "audio_change_inconclusive"


EXPLANATIONS = {
    "no_visible_revision_in_window": "The sampled V1/V2 frames are essentially unchanged throughout the evidence window; the requested visual revision is not visible.",
    "semantic_conflicts_with_unchanged_frames": "Semantic output claims success but the frames are essentially unchanged. Conflicting evidence requires review.",
    "requested_after_state_observed": "The requested after state is visible in semantic evidence and supported by a measurable frame change.",
    "requested_after_state_contradicted": "Semantic inspection found visible evidence contradicting the requested after state.",
    "exact_after_text_unconfirmed": "The exact requested replacement wording was not confirmed. Pixel differences alone cannot prove a text revision.",
    "exact_crop_percentage_unmeasured": "A crop may be visible, but the exact requested percentage has not been measured.",
    "local_audio_muted": "Audio in the local window dropped from active sound to near-silence, with at least an 80% energy reduction.",
    "local_audio_retained": "Audio remains active in the requested window with most of its original energy.",
    "local_silence_removed_with_aligned_flanks": "A bounded V1 silence interval is shorter in V2; independently matched footage before and after it confirms a local cut.",
    "local_pause_retained": "Matched footage on both sides retains its timing and the local silence remains in V2.",
}


def verify(req: RevisionRequest, v1: Path, v2: Path, evidence_dir: Path) -> VerificationResult:
    d1, d2 = duration_seconds(v1), duration_seconds(v2)
    ts = req.timestamp_seconds
    if ts is None or ts < 0 or ts >= min(d1, d2) - 0.05:
        return VerificationResult(request=req, verdict=Verdict.REVIEW, confidence=0.3,
            evidence=Evidence(timestamp_seconds=ts, explanation="A timestamp inside both exports is required; no substitute moment was checked.",
                              reason_codes=["missing_or_out_of_range_timestamp"], methods=["timestamp_validation"]))
    times = sorted({max(0, ts - 0.5), ts, min(ts + 0.5, min(d1, d2) - 0.05)})
    frames = []
    evidence_frames = []
    deltas, matches = [], []
    for i, moment in enumerate(times):
        before = extract_frame(v1, moment, evidence_dir / f"{req.id}-v1-{i}.jpg")
        after = extract_frame(v2, moment, evidence_dir / f"{req.id}-v2-{i}.jpg")
        frames.append((moment, before, after))
        for version, path in (("V1", before), ("V2", after)):
            evidence_frames.append(EvidenceFrame(version=version, timestamp_seconds=moment,
                path=f"/evidence/{evidence_dir.name}/{path.name}"))
        delta, match = visual_difference(v1, v2, moment)
        deltas.append(delta)
        matches.append(match)
    center = times.index(ts)
    metrics = [EvidenceMetric(name="visual_delta", v1=0, v2=deltas[center], delta=deltas[center], unit="0-1"),
               EvidenceMetric(name="feature_match", v2=matches[center], unit="0-1")]
    metrics += [EvidenceMetric(name=f"visual_delta_frame_{i}", v2=d, unit="0-1") for i, d in enumerate(deltas)]
    methods = ["multi_frame_difference", "orb_feature_match"]
    semantic, status = None, "not_requested"
    agreement = "deterministic_only"
    thresholds = dict(VISUAL_THRESHOLDS)
    window_start, window_end = times[0], times[-1]
    if req.kind == CheckKind.MUTE_AUDIO:
        methods.append("local_audio_rms")
        thresholds = dict(AUDIO_THRESHOLDS)
        window_start = max(0, ts - req.window_seconds / 2)
        window_end = min(min(d1, d2), window_start + req.window_seconds)
        if not has_audio(v1):
            verdict, confidence, code = Verdict.REVIEW, 0.35, "source_audio_unavailable"
        else:
            window = window_end - window_start
            audio_center = window_start + window / 2
            a1 = audio_rms(v1, audio_center, window)
            a2 = audio_rms(v2, audio_center, window) if has_audio(v2) else 0.0
            metrics += [EvidenceMetric(name="audio_rms", v1=a1, v2=a2, delta=a2-a1, unit="RMS"),
                        EvidenceMetric(name="audio_ratio_v2_to_v1", v1=1, v2=a2/max(a1, 1e-6), unit="ratio")]
            verdict, confidence, code = check_mute(a1, a2)
    elif req.kind == CheckKind.REMOVE_PAUSE:
        methods += ["local_silence_envelope", "two_flank_temporal_alignment"]
        thresholds = dict(PAUSE_THRESHOLDS)
        verdict_raw, confidence, code, signals = check_pause(v1, v2, ts)
        verdict = Verdict(verdict_raw)
        metrics += [EvidenceMetric(name=k, v2=v) for k, v in signals.items()]
        window_start, window_end = max(0, ts - 3), min(d1, ts + 3)
        for flank in ("pre", "post"):
            if f"{flank}_anchor_time" in signals:
                moment = signals[f"{flank}_anchor_time"]
                for version, video, when in (("V1", v1, moment), ("V2", v2, moment + signals[f"{flank}_offset"])):
                    path = extract_frame(video, when, evidence_dir / f"{req.id}-{flank}-{version}.jpg")
                    evidence_frames.append(EvidenceFrame(version=version, timestamp_seconds=when,
                        path=f"/evidence/{evidence_dir.name}/{path.name}"))
    elif req.kind in {CheckKind.TEXT_CHANGE, CheckKind.ZOOM_CROP, CheckKind.VISUAL_CHANGE}:
        semantic, status = verify_semantic(req, frames)
        if semantic:
            methods.append("gemini_temporal_window")
        verdict, confidence, code, agreement = fuse_visual(req, deltas, semantic)
    else:
        verdict, confidence, code = Verdict.REVIEW, 0.35, "unsupported_revision_intent"
    evidence = Evidence(timestamp_seconds=ts,
        v1_frame_path=evidence_frames[2*center].path, v2_frame_path=evidence_frames[2*center+1].path,
        metrics=metrics, explanation=EXPLANATIONS.get(code, "Evidence is insufficient for an automatic verdict: " + code.replace("_", " ") + "."),
        methods=methods, reason_codes=[code], thresholds=thresholds, frames=evidence_frames,
        window_start_seconds=window_start, window_end_seconds=window_end,
        semantic_status=status, signal_agreement=agreement,
        before_observation=semantic.before_observation if semantic else None,
        after_observation=semantic.after_observation if semantic else None,
        semantic_confidence=semantic.confidence if semantic else None,
        semantic_supporting_frame_indices=semantic.supporting_frame_indices if semantic else [],
        observed_after_text=semantic.observed_after_text if semantic else None)
    return VerificationResult(request=req, verdict=verdict, confidence=confidence, evidence=evidence)
