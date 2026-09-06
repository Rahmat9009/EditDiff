from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .media import (
    MediaError,
    audio_envelope,
    audio_rms,
    duration_seconds,
    extract_frame,
    frame_gray,
    has_audio,
    probe_media,
)
from .models import (
    ChangeConfidence,
    ChangeEvidence,
    ChangeKind,
    DetectedChange,
    DiscoverResponse,
    DiscoverSummary,
    EvidenceMetric,
)

# Deterministic threshold constants
VISUAL_MATCH_THRESHOLD = 0.08      # L1 thumbnail distance below which frames match
VISUAL_CHANGE_MIN = 0.04           # Minimum mean abs diff on full verification frame to confirm change
VISUAL_HIGH_CONF_MIN = 0.07        # High confidence visual threshold
VISUAL_ORB_MATCH_MAX = 0.40        # Maximum ORB match ratio for high confidence visual replacement
NOISE_DIFF_MAX = 0.02              # Under this diff, considered encoding noise / negligible
NOISE_ORB_MATCH_MIN = 0.70         # High feature match confirms encoding noise
FLANK_VISUAL_MAX = 0.08            # Visual distance threshold for a stable matching flank

AUDIO_ACTIVE_MIN = 0.008           # Minimum RMS to consider audio active
AUDIO_SILENT_MAX = 0.004           # Maximum RMS to consider audio near-silent
AUDIO_MUTE_DROP_RATIO = 0.25       # Final/Pre energy ratio for mute detection
AUDIO_SHIFT_RATIO = 0.60           # Energy shift ratio to trigger audio change

DP_GAP_COST = 0.28                 # Penalty for insertion / deletion in DP alignment
DP_SUB_CAP = 0.38                  # Cap on substitution distance in DP alignment
MAX_SAMPLES = 1200                 # Maximum samples per video to bound memory/CPU
MIN_BAND_SECONDS = 30.0            # Minimum Sakoe-Chiba band width in seconds
SAFETY_MARGIN_SECONDS = 15.0       # Added to absolute duration delta for adaptive band
MAX_BAND_CAP_SECONDS = 120.0       # Maximum supported cumulative drift / band width (memory bound)


@dataclass
class VideoSample:
    index: int
    timestamp: float
    thumb: np.ndarray              # 32x18 normalized float32 grayscale
    audio_rms: float | None        # None if audio unavailable or processing failed


def visual_difference_at(path1: Path, t1: float, path2: Path, t2: float) -> tuple[float, float]:
    """Compute mean abs difference and ORB match ratio between frames at two arbitrary timestamps."""
    a = frame_gray(path1, t1)
    b = frame_gray(path2, t2)
    diff = cv2.absdiff(a, b)
    mean_abs = float(np.mean(diff) / 255.0)

    orb = cv2.ORB_create(nfeatures=800)
    k1, d1 = orb.detectAndCompute(a, None)
    k2, d2 = orb.detectAndCompute(b, None)
    match_ratio = 0.0
    if d1 is not None and d2 is not None and len(k1) and len(k2):
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = matcher.match(d1, d2)
        good = [m for m in matches if m.distance < 45]
        match_ratio = len(good) / max(min(len(k1), len(k2)), 1)
    return mean_abs, match_ratio


def sample_video(path: Path, step: float) -> list[VideoSample]:
    """
    Sample video deterministically at regular intervals with compact visual descriptors.
    Audio measurement explicitly differentiates between known silence (no audio stream)
    and processing failure (represented as None).
    """
    dur = duration_seconds(path)
    if dur <= 0:
        return []

    # Audio envelope across full video (single ffmpeg pass)
    audio_env = None
    audio_has_stream = False
    audio_failed = False
    try:
        audio_has_stream = has_audio(path)
        if audio_has_stream:
            audio_env = audio_envelope(path, 0, dur, step=0.1)
    except Exception:
        audio_failed = True
        audio_env = None

    cap = cv2.VideoCapture(str(path))
    samples: list[VideoSample] = []
    t = 0.0
    idx = 0
    while t < dur - 0.02 and idx < MAX_SAMPLES:
        cap.set(cv2.CAP_PROP_POS_MSEC, max(t, 0.0) * 1000.0)
        ok, frame = cap.read()
        if not ok or frame is None:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        thumb = cv2.resize(gray, (32, 18), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0

        # Local audio RMS from precomputed envelope
        sample_audio: float | None = None
        if audio_has_stream:
            if audio_failed or audio_env is None:
                # Audio stream exists but decoding/envelope failed -> unavailable
                sample_audio = None
            else:
                env_idx_start = max(0, int((t - step / 2) / 0.1))
                env_idx_end = min(len(audio_env), int(math.ceil((t + step / 2) / 0.1)))
                if env_idx_end > env_idx_start:
                    sample_audio = float(np.mean(audio_env[env_idx_start:env_idx_end]))
                else:
                    sample_audio = None
        else:
            # Video legitimately has no audio track -> known silent (0.0)
            sample_audio = 0.0

        samples.append(VideoSample(index=idx, timestamp=round(t, 3), thumb=thumb, audio_rms=sample_audio))
        t += step
        idx += 1

    cap.release()
    return samples


@dataclass
class AlignmentStep:
    kind: str                      # "MATCH", "REPLACE", "DELETE", "INSERT"
    i: int | None
    j: int | None
    t1: float | None
    t2: float | None
    d_vis: float
    a1: float | None
    a2: float | None


@dataclass
class AlignmentResult:
    path: list[AlignmentStep]
    band_overflow: bool


def align_sequences_banded(
    s1: list[VideoSample],
    s2: list[VideoSample],
    step: float,
    band_seconds: float = MIN_BAND_SECONDS,
) -> AlignmentResult:
    """
    Dynamic programming sequence alignment constrained by a Sakoe-Chiba band.
    Complexity: O(N * W) time and memory, where W is the band half-width.
    """
    n = len(s1)
    m = len(s2)
    if n == 0 and m == 0:
        return AlignmentResult([], False)
    if n == 0:
        return AlignmentResult([
            AlignmentStep("INSERT", None, j, None, s2[j].timestamp, 1.0, 0.0, s2[j].audio_rms)
            for j in range(m)
        ], False)
    if m == 0:
        return AlignmentResult([
            AlignmentStep("DELETE", i, None, s1[i].timestamp, None, 1.0, s1[i].audio_rms, 0.0)
            for i in range(n)
        ], False)

    w = max(5, int(math.ceil(band_seconds / step)))
    INF = 1e9

    # dp[i, offset] where offset = (j - i) + w
    # Valid offset range: 0 .. 2*w
    band_width = 2 * w + 1
    dp = np.full((n + 1, band_width), INF, dtype=np.float32)
    back_action = np.zeros((n + 1, band_width), dtype=np.int8)

    # Base state: (0, 0) -> i=0, j=0 -> offset = w
    dp[0, w] = 0.0

    for i in range(n + 1):
        for k in range(band_width):
            j = i + (k - w)
            if j < 0 or j > m:
                continue
            cur = dp[i, k]
            if cur >= INF:
                continue

            # 1. Diagonal transition: (i -> i+1, j -> j+1)
            if i < n and j < m:
                d = float(np.mean(np.abs(s1[i].thumb - s2[j].thumb)))
                cost = cur + min(d, DP_SUB_CAP)
                if cost < dp[i + 1, k]:
                    dp[i + 1, k] = cost
                    back_action[i + 1, k] = 1

            # 2. Deletion in s1: (i -> i+1, j)
            if i < n:
                next_k = k - 1
                if 0 <= next_k < band_width:
                    cost = cur + DP_GAP_COST
                    if cost < dp[i + 1, next_k]:
                        dp[i + 1, next_k] = cost
                        back_action[i + 1, next_k] = 2

            # 3. Insertion in s2: (i, j -> j+1)
            if j < m:
                next_k = k + 1
                if 0 <= next_k < band_width:
                    cost = cur + DP_GAP_COST
                    if cost < dp[i, next_k]:
                        dp[i, next_k] = cost
                        back_action[i, next_k] = 3

    # Traceback from (n, m)
    curr_i = n
    curr_k = (m - n) + w
    band_overflow = False
    if curr_k < 0 or curr_k >= band_width or dp[curr_i, curr_k] >= INF:
        band_overflow = True
        valid_ks = [k for k in range(band_width) if dp[n, k] < INF]
        if valid_ks:
            curr_k = min(valid_ks, key=lambda k: abs((n + k - w) - m))
        else:
            curr_k = w

    path: list[AlignmentStep] = []
    while curr_i > 0 or (curr_i + (curr_k - w)) > 0:
        curr_j = curr_i + (curr_k - w)
        act = back_action[curr_i, curr_k]
        if act == 1:
            # Diagonal
            prev_i = curr_i - 1
            prev_j = curr_j - 1
            prev_k = curr_k
            d = float(np.mean(np.abs(s1[prev_i].thumb - s2[prev_j].thumb)))
            step_kind = "MATCH" if d < VISUAL_MATCH_THRESHOLD else "REPLACE"
            path.append(AlignmentStep(
                kind=step_kind,
                i=prev_i,
                j=prev_j,
                t1=s1[prev_i].timestamp,
                t2=s2[prev_j].timestamp,
                d_vis=d,
                a1=s1[prev_i].audio_rms,
                a2=s2[prev_j].audio_rms,
            ))
            curr_i, curr_k = prev_i, prev_k
        elif act == 2:
            # Deletion in s1
            prev_i = curr_i - 1
            prev_k = curr_k + 1
            path.append(AlignmentStep(
                kind="DELETE",
                i=prev_i,
                j=None,
                t1=s1[prev_i].timestamp,
                t2=s2[min(max(0, curr_j), m - 1)].timestamp if m > 0 else None,
                d_vis=1.0,
                a1=s1[prev_i].audio_rms,
                a2=None,
            ))
            curr_i, curr_k = prev_i, prev_k
        elif act == 3:
            # Insertion in s2
            prev_j = curr_j - 1
            prev_k = curr_k - 1
            path.append(AlignmentStep(
                kind="INSERT",
                i=None,
                j=prev_j,
                t1=s1[min(max(0, curr_i), n - 1)].timestamp if n > 0 else None,
                t2=s2[prev_j].timestamp,
                d_vis=1.0,
                a1=None,
                a2=s2[prev_j].audio_rms,
            ))
            curr_k = prev_k
        else:
            band_overflow = True
            break

    path.reverse()
    return AlignmentResult(path, band_overflow)


@dataclass
class CandidateRegion:
    kind: str                      # "VISUAL", "TIMING_DELETE", "TIMING_INSERT", "AUDIO"
    t1_start: float | None
    t1_end: float | None
    t2_start: float | None
    t2_end: float | None
    start_step_idx: int
    end_step_idx: int
    steps: list[AlignmentStep]


def coalesce_candidate_regions(path: list[AlignmentStep], step: float) -> list[CandidateRegion]:
    """
    Coalesces consecutive alignment anomaly steps into candidate regions.
    Bridges tiny single-sample flickers and tracks index boundaries for flank inspection.
    """
    if not path:
        return []

    tagged: list[str] = []
    for s in path:
        if s.kind == "DELETE":
            tagged.append("TIMING_DELETE")
        elif s.kind == "INSERT":
            tagged.append("TIMING_INSERT")
        elif s.kind == "REPLACE":
            tagged.append("VISUAL")
        elif s.kind == "MATCH":
            a1, a2 = s.a1, s.a2
            # Audio change check: strictly requires available audio measurements on both sides
            if a1 is not None and a2 is not None:
                is_mute = (a1 >= AUDIO_ACTIVE_MIN and a2 <= AUDIO_SILENT_MAX and (a2 / max(a1, 1e-6)) <= AUDIO_MUTE_DROP_RATIO)
                is_unmute = (a1 <= AUDIO_SILENT_MAX and a2 >= AUDIO_ACTIVE_MIN)
                major_shift = (max(a1, a2) >= AUDIO_ACTIVE_MIN and abs(a1 - a2) / max(a1, a2) >= AUDIO_SHIFT_RATIO)
                if is_mute or is_unmute or major_shift:
                    tagged.append("AUDIO")
                else:
                    tagged.append("NONE")
            else:
                tagged.append("NONE")
        else:
            tagged.append("NONE")

    smoothed = list(tagged)
    for i in range(1, len(smoothed) - 1):
        if smoothed[i] == "NONE" and smoothed[i - 1] == smoothed[i + 1] and smoothed[i - 1] != "NONE":
            smoothed[i] = smoothed[i - 1]

    regions: list[CandidateRegion] = []
    current_tag = "NONE"
    current_steps: list[AlignmentStep] = []
    current_start_idx = 0

    for idx, (tag, step_item) in enumerate(zip(smoothed, path)):
        if tag != current_tag:
            if current_tag != "NONE" and current_steps:
                t1s = [st.t1 for st in current_steps if st.t1 is not None]
                t2s = [st.t2 for st in current_steps if st.t2 is not None]
                regions.append(CandidateRegion(
                    kind=current_tag,
                    t1_start=min(t1s) if t1s else None,
                    t1_end=max(t1s) if t1s else None,
                    t2_start=min(t2s) if t2s else None,
                    t2_end=max(t2s) if t2s else None,
                    start_step_idx=current_start_idx,
                    end_step_idx=idx - 1,
                    steps=current_steps,
                ))
            current_tag = tag
            current_start_idx = idx
            current_steps = [step_item] if tag != "NONE" else []
        else:
            if current_tag != "NONE":
                current_steps.append(step_item)

    if current_tag != "NONE" and current_steps:
        t1s = [st.t1 for st in current_steps if st.t1 is not None]
        t2s = [st.t2 for st in current_steps if st.t2 is not None]
        regions.append(CandidateRegion(
            kind=current_tag,
            t1_start=min(t1s) if t1s else None,
            t1_end=max(t1s) if t1s else None,
            t2_start=min(t2s) if t2s else None,
            t2_end=max(t2s) if t2s else None,
            start_step_idx=current_start_idx,
            end_step_idx=len(path) - 1,
            steps=current_steps,
        ))

    return regions


def classify_and_verify_changes(
    regions: list[CandidateRegion],
    alignment_path: list[AlignmentStep],
    step: float,
    v1_path: Path,
    v2_path: Path,
    evidence_dir: Path,
    d1: float,
    d2: float,
) -> list[DetectedChange]:
    """
    Confirms candidate regions using full frame extraction, deterministic flank verification,
    conservative reason codes, and creates evidence JPGs only for confirmed changes.
    """
    detected: list[DetectedChange] = []

    for idx, reg in enumerate(regions):
        change_id = f"change-{idx + 1:03d}"

        if reg.kind == "VISUAL":
            t1_mid = (reg.t1_start + reg.t1_end) / 2 if (reg.t1_start is not None and reg.t1_end is not None) else (reg.t1_start or 0.0)
            t2_mid = (reg.t2_start + reg.t2_end) / 2 if (reg.t2_start is not None and reg.t2_end is not None) else (reg.t2_start or 0.0)

            mean_abs, match_ratio = visual_difference_at(v1_path, t1_mid, v2_path, t2_mid)

            if mean_abs <= NOISE_DIFF_MAX and match_ratio >= NOISE_ORB_MATCH_MIN:
                continue
            if mean_abs < VISUAL_CHANGE_MIN:
                continue

            p1_img = extract_frame(v1_path, t1_mid, evidence_dir / f"{change_id}-pre.jpg")
            p2_img = extract_frame(v2_path, t2_mid, evidence_dir / f"{change_id}-final.jpg")

            confidence = (
                ChangeConfidence.HIGH
                if (mean_abs >= VISUAL_HIGH_CONF_MIN and match_ratio <= VISUAL_ORB_MATCH_MAX)
                else ChangeConfidence.MEDIUM
            )

            metrics = [
                EvidenceMetric(name="mean_absolute_difference", v1=0.0, v2=round(mean_abs, 4), delta=round(mean_abs, 4), unit="0-1"),
                EvidenceMetric(name="orb_match_ratio", v2=round(match_ratio, 4), unit="0-1"),
            ]

            evidence = ChangeEvidence(
                pre_final_timestamp_seconds=round(t1_mid, 3),
                final_timestamp_seconds=round(t2_mid, 3),
                window_start_pre_final=reg.t1_start,
                window_end_pre_final=reg.t1_end,
                window_start_final=reg.t2_start,
                window_end_final=reg.t2_end,
                pre_final_frame_path=f"/evidence/{evidence_dir.name}/{p1_img.name}",
                final_frame_path=f"/evidence/{evidence_dir.name}/{p2_img.name}",
                metrics=metrics,
                methods=["bounded_sequence_alignment", "mean_frame_difference", "orb_feature_match"],
                reason_codes=["aligned_visual_difference"],
                explanation="The aligned visual content differs materially between versions.",
            )

            detected.append(DetectedChange(
                id=change_id,
                kind=ChangeKind.VISUAL,
                confidence=confidence,
                title="VISUAL CHANGE",
                description="The aligned visual content differs materially between versions.",
                evidence=evidence,
            ))

        elif reg.kind in ("TIMING_DELETE", "TIMING_INSERT"):
            is_delete = (reg.kind == "TIMING_DELETE")

            # Mathematically accurate gap duration from sampled count and step interval
            gap_duration = round(len(reg.steps) * step, 3)
            if gap_duration < 0.2:
                continue

            # Real Flank Verification
            # Find nearest preceding and following MATCH steps in alignment_path
            pre_flank = None
            for k in range(reg.start_step_idx - 1, -1, -1):
                if alignment_path[k].kind == "MATCH":
                    pre_flank = alignment_path[k]
                    break

            post_flank = None
            for k in range(reg.end_step_idx + 1, len(alignment_path)):
                if alignment_path[k].kind == "MATCH":
                    post_flank = alignment_path[k]
                    break

            has_pre_flank = (pre_flank is not None and pre_flank.d_vis <= FLANK_VISUAL_MAX and pre_flank.t1 is not None and pre_flank.t2 is not None)
            has_post_flank = (post_flank is not None and post_flank.d_vis <= FLANK_VISUAL_MAX and post_flank.t1 is not None and post_flank.t2 is not None)

            offset_before = (pre_flank.t2 - pre_flank.t1) if has_pre_flank else None
            offset_after = (post_flank.t2 - post_flank.t1) if has_post_flank else None
            pre_vis_dist = round(pre_flank.d_vis, 4) if has_pre_flank else None
            post_vis_dist = round(post_flank.d_vis, 4) if has_post_flank else None

            inferred_timing_delta = None
            offset_consistent = False
            if offset_before is not None and offset_after is not None:
                inferred_timing_delta = round(offset_after - offset_before, 3)
                expected_delta = -gap_duration if is_delete else gap_duration
                # Tolerance based on adaptive sample interval
                tolerance = max(0.5, 1.5 * step)
                offset_consistent = abs(inferred_timing_delta - expected_delta) <= tolerance

            # Determine confidence, classification, and reason codes conservatively
            methods = ["bounded_sequence_alignment"]
            if has_pre_flank and has_post_flank and offset_consistent:
                confidence = ChangeConfidence.HIGH
                kind = ChangeKind.TIMING
                methods.append("temporal_anchor_verification")
                code = "segment_removed_with_aligned_flanks" if is_delete else "segment_inserted_with_aligned_flanks"
            elif has_pre_flank or has_post_flank:
                confidence = ChangeConfidence.MEDIUM
                kind = ChangeKind.TIMING
                code = "timing_change_single_flank"
            else:
                confidence = ChangeConfidence.LOW
                kind = ChangeKind.REVIEW
                code = "timing_alignment_ambiguous"

            # Frame extraction
            if is_delete:
                t1_mid = (reg.t1_start + reg.t1_end) / 2 if (reg.t1_start is not None and reg.t1_end is not None) else 0.0
                final_anchor = reg.t2_start if reg.t2_start is not None else min(t1_mid, d2 - 0.05)
                p1_img = extract_frame(v1_path, t1_mid, evidence_dir / f"{change_id}-pre.jpg")
                p2_img = extract_frame(v2_path, final_anchor, evidence_dir / f"{change_id}-final.jpg")
                win_start_pre, win_end_pre = reg.t1_start, reg.t1_end
                win_start_post, win_end_post = round(final_anchor, 3), round(final_anchor, 3)
                ts_pre, ts_post = round(t1_mid, 3), round(final_anchor, 3)
                action_text = "removed from"
                dur_metric_name = "removed_duration_seconds"
                dur_delta = -gap_duration
            else:
                t2_mid = (reg.t2_start + reg.t2_end) / 2 if (reg.t2_start is not None and reg.t2_end is not None) else 0.0
                pre_anchor = reg.t1_start if reg.t1_start is not None else min(t2_mid, d1 - 0.05)
                p1_img = extract_frame(v1_path, pre_anchor, evidence_dir / f"{change_id}-pre.jpg")
                p2_img = extract_frame(v2_path, t2_mid, evidence_dir / f"{change_id}-final.jpg")
                win_start_pre, win_end_pre = round(pre_anchor, 3), round(pre_anchor, 3)
                win_start_post, win_end_post = reg.t2_start, reg.t2_end
                ts_pre, ts_post = round(pre_anchor, 3), round(t2_mid, 3)
                action_text = "inserted into"
                dur_metric_name = "inserted_duration_seconds"
                dur_delta = gap_duration

            metrics = [
                EvidenceMetric(name=dur_metric_name, delta=round(dur_delta, 3), unit="seconds"),
                EvidenceMetric(name="pre_flank_visual_distance", v2=pre_vis_dist, unit="0-1"),
                EvidenceMetric(name="post_flank_visual_distance", v2=post_vis_dist, unit="0-1"),
                EvidenceMetric(name="offset_before_seconds", delta=round(offset_before, 3) if offset_before is not None else None, unit="seconds"),
                EvidenceMetric(name="offset_after_seconds", delta=round(offset_after, 3) if offset_after is not None else None, unit="seconds"),
                EvidenceMetric(name="inferred_timing_delta_seconds", delta=round(inferred_timing_delta, 3) if inferred_timing_delta is not None else None, unit="seconds"),
            ]

            if kind == ChangeKind.TIMING:
                title = "TIMING CHANGE"
                explanation = f"Approximately {gap_duration:.1f} seconds of material was {action_text} this region."
            else:
                title = "TIMING REVIEW"
                explanation = "Timing discrepancy detected, but stable alignment anchors could not be verified on flanking footage."

            evidence = ChangeEvidence(
                pre_final_timestamp_seconds=ts_pre,
                final_timestamp_seconds=ts_post,
                window_start_pre_final=win_start_pre,
                window_end_pre_final=win_end_pre,
                window_start_final=win_start_post,
                window_end_final=win_end_post,
                pre_final_frame_path=f"/evidence/{evidence_dir.name}/{p1_img.name}",
                final_frame_path=f"/evidence/{evidence_dir.name}/{p2_img.name}",
                metrics=metrics,
                methods=methods,
                reason_codes=[code],
                explanation=explanation,
            )

            detected.append(DetectedChange(
                id=change_id,
                kind=kind,
                confidence=confidence,
                title=title,
                description=explanation,
                evidence=evidence,
            ))

        elif reg.kind == "AUDIO":
            t1_mid = (reg.t1_start + reg.t1_end) / 2 if (reg.t1_start is not None and reg.t1_end is not None) else (reg.t1_start or 0.0)
            t2_mid = (reg.t2_start + reg.t2_end) / 2 if (reg.t2_start is not None and reg.t2_end is not None) else (reg.t2_start or 0.0)

            win = max(0.5, (reg.t1_end or t1_mid) - (reg.t1_start or t1_mid))

            # Never interpret audio processing failure as silence
            if not has_audio(v1_path) and not has_audio(v2_path):
                continue
            try:
                a1 = audio_rms(v1_path, t1_mid, window=win) if has_audio(v1_path) else 0.0
            except Exception:
                a1 = None
            try:
                a2 = audio_rms(v2_path, t2_mid, window=win) if has_audio(v2_path) else 0.0
            except Exception:
                a2 = None

            if a1 is None or a2 is None:
                # Audio measurement unavailable -> never emit false audio changes
                continue

            ratio = a2 / max(a1, 1e-6)
            drop_pct = round((1.0 - ratio) * 100.0)

            if a1 >= AUDIO_ACTIVE_MIN and a2 <= AUDIO_SILENT_MAX and ratio <= AUDIO_MUTE_DROP_RATIO:
                code = "local_audio_muted"
                explanation = f"Final export audio energy is approximately {drop_pct}% lower in this aligned window."
                conf = ChangeConfidence.HIGH
            elif a1 <= AUDIO_SILENT_MAX and a2 >= AUDIO_ACTIVE_MIN:
                code = "local_audio_added"
                explanation = "Final export has active audio energy in a previously silent window."
                conf = ChangeConfidence.HIGH
            elif max(a1, a2) >= AUDIO_ACTIVE_MIN and abs(a1 - a2) / max(a1, a2) >= AUDIO_SHIFT_RATIO:
                code = "local_audio_energy_shifted"
                shift_dir = "lower" if a2 < a1 else "higher"
                explanation = f"Final export audio energy is materially {shift_dir} in this aligned window."
                conf = ChangeConfidence.MEDIUM
            else:
                continue

            p1_img = extract_frame(v1_path, t1_mid, evidence_dir / f"{change_id}-pre.jpg")
            p2_img = extract_frame(v2_path, t2_mid, evidence_dir / f"{change_id}-final.jpg")

            metrics = [
                EvidenceMetric(name="audio_rms", v1=round(a1, 4), v2=round(a2, 4), delta=round(a2 - a1, 4), unit="RMS"),
                EvidenceMetric(name="audio_ratio_final_to_pre", v1=1.0, v2=round(ratio, 3), unit="ratio"),
            ]

            evidence = ChangeEvidence(
                pre_final_timestamp_seconds=round(t1_mid, 3),
                final_timestamp_seconds=round(t2_mid, 3),
                window_start_pre_final=reg.t1_start,
                window_end_pre_final=reg.t1_end,
                window_start_final=reg.t2_start,
                window_end_final=reg.t2_end,
                pre_final_frame_path=f"/evidence/{evidence_dir.name}/{p1_img.name}",
                final_frame_path=f"/evidence/{evidence_dir.name}/{p2_img.name}",
                metrics=metrics,
                methods=["bounded_sequence_alignment", "local_audio_rms_envelope"],
                reason_codes=[code],
                explanation=explanation,
            )

            detected.append(DetectedChange(
                id=change_id,
                kind=ChangeKind.AUDIO,
                confidence=conf,
                title="AUDIO CHANGE",
                description=explanation,
                evidence=evidence,
            ))

    return detected


def discover_changes(pre_final_path: Path, final_path: Path, evidence_dir: Path) -> DiscoverResponse:
    """
    Main entry point for Discover Changes workflow.
    Validates media, samples visual/audio descriptors, runs bounded adaptive DP alignment,
    coalesces candidate change regions, and produces an evidence-first DiscoverResponse.
    """
    probe_media(pre_final_path)
    probe_media(final_path)

    d1 = duration_seconds(pre_final_path)
    d2 = duration_seconds(final_path)
    duration_delta = abs(d1 - d2)

    # Check for alignment band overflow: if duration delta exceeds maximum memory-bounded cap
    if duration_delta > (MAX_BAND_CAP_SECONDS - 5.0):
        # Explicit REVIEW change: timeline divergence exceeds automatic alignment limit
        review_change = DetectedChange(
            id="change-001",
            kind=ChangeKind.REVIEW,
            confidence=ChangeConfidence.LOW,
            title="TIMELINE DIVERGENCE REVIEW",
            description="The duration difference between video versions exceeds the maximum supported alignment band (120 seconds). Automatic alignment could not be completed reliably.",
            evidence=ChangeEvidence(
                explanation="Timeline divergence between pre-final and final exceeds the 120-second automatic alignment limit.",
                methods=["bounded_sequence_alignment"],
                reason_codes=["timeline_divergence_exceeds_band"],
            ),
        )
        return DiscoverResponse(
            report_id=evidence_dir.name,
            pre_final_duration_seconds=round(d1, 3),
            final_duration_seconds=round(d2, 3),
            duration_delta_seconds=round(d2 - d1, 3),
            summary=DiscoverSummary(total_changes=1, visual=0, timing=0, audio=0, text=0, review=1),
            changes=[review_change],
        )

    # Adaptive sample interval (0.5s for normal videos; scaled up for very long videos to bound to MAX_SAMPLES)
    max_dur = max(d1, d2)
    step = 0.5 if max_dur <= 300.0 else max(0.5, max_dur / 600.0)

    # Adaptive band: max(MIN_BAND_SECONDS, duration_delta + SAFETY_MARGIN_SECONDS), capped at MAX_BAND_CAP_SECONDS
    band_seconds = min(MAX_BAND_CAP_SECONDS, max(MIN_BAND_SECONDS, duration_delta + SAFETY_MARGIN_SECONDS))

    s1 = sample_video(pre_final_path, step=step)
    s2 = sample_video(final_path, step=step)

    alignment = align_sequences_banded(s1, s2, step=step, band_seconds=band_seconds)
    candidate_regions = coalesce_candidate_regions(alignment.path, step=step)
    changes = classify_and_verify_changes(
        candidate_regions,
        alignment.path,
        step=step,
        v1_path=pre_final_path,
        v2_path=final_path,
        evidence_dir=evidence_dir,
        d1=d1,
        d2=d2,
    )

    # If alignment hit boundary overflow during traceback, append an explicit REVIEW change
    if alignment.band_overflow:
        overflow_change = DetectedChange(
            id=f"change-{len(changes) + 1:03d}",
            kind=ChangeKind.REVIEW,
            confidence=ChangeConfidence.LOW,
            title="TIMELINE ALIGNMENT REVIEW",
            description="Timeline divergence approached the boundary of the automatic alignment band; tail footage may be partially unverified.",
            evidence=ChangeEvidence(
                explanation="Alignment path encountered the temporal search boundary.",
                methods=["bounded_sequence_alignment"],
                reason_codes=["alignment_band_boundary_encountered"],
            ),
        )
        changes.append(overflow_change)

    summary = DiscoverSummary(
        total_changes=len(changes),
        visual=sum(1 for c in changes if c.kind == ChangeKind.VISUAL),
        timing=sum(1 for c in changes if c.kind == ChangeKind.TIMING),
        audio=sum(1 for c in changes if c.kind == ChangeKind.AUDIO),
        text=sum(1 for c in changes if c.kind == ChangeKind.TEXT),
        review=sum(1 for c in changes if c.kind == ChangeKind.REVIEW),
    )

    return DiscoverResponse(
        report_id=evidence_dir.name,
        pre_final_duration_seconds=round(d1, 3),
        final_duration_seconds=round(d2, 3),
        duration_delta_seconds=round(d2 - d1, 3),
        summary=summary,
        changes=changes,
    )
