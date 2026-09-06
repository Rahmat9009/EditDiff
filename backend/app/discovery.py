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

AUDIO_ACTIVE_MIN = 0.008           # Minimum RMS to consider audio active
AUDIO_SILENT_MAX = 0.004           # Maximum RMS to consider audio near-silent
AUDIO_MUTE_DROP_RATIO = 0.25       # Final/Pre energy ratio for mute detection
AUDIO_SHIFT_RATIO = 0.60           # Energy shift ratio to trigger audio change

DP_GAP_COST = 0.28                 # Penalty for insertion / deletion in DP alignment
DP_SUB_CAP = 0.38                  # Cap on substitution distance in DP alignment
MAX_SAMPLES = 1200                 # Maximum samples per video to bound memory/CPU
MAX_BAND_SECONDS = 30.0            # Sakoe-Chiba band width in seconds


@dataclass
class VideoSample:
    index: int
    timestamp: float
    thumb: np.ndarray              # 32x18 normalized float32 grayscale
    audio_rms: float


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
    """Sample video deterministically at regular intervals with compact visual descriptors."""
    dur = duration_seconds(path)
    if dur <= 0:
        return []

    # Audio envelope across full video (single ffmpeg pass)
    audio_env = None
    if has_audio(path):
        try:
            audio_env = audio_envelope(path, 0, dur, step=0.1)
        except Exception:
            audio_env = None

    cap = cv2.VideoCapture(str(path))
    samples: list[VideoSample] = []
    t = 0.0
    idx = 0
    while t < dur - 0.02 and idx < MAX_SAMPLES:
        cap.set(cv2.CAP_PROP_POS_MSEC, max(t, 0.0) * 1000.0)
        ok, frame = cap.read()
        if not ok or frame is None:
            # If reading at the very end fails, break
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        thumb = cv2.resize(gray, (32, 18), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0

        # Local audio RMS from precomputed envelope
        sample_audio = 0.0
        if audio_env is not None and len(audio_env) > 0:
            env_idx_start = max(0, int((t - step / 2) / 0.1))
            env_idx_end = min(len(audio_env), int(math.ceil((t + step / 2) / 0.1)))
            if env_idx_end > env_idx_start:
                sample_audio = float(np.mean(audio_env[env_idx_start:env_idx_end]))

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
    a1: float
    a2: float


def align_sequences_banded(
    s1: list[VideoSample],
    s2: list[VideoSample],
    step: float,
    band_seconds: float = MAX_BAND_SECONDS,
) -> list[AlignmentStep]:
    """
    Dynamic programming sequence alignment constrained by a Sakoe-Chiba band.
    Complexity: O(N * W) time and memory, where W is the band half-width.
    """
    n = len(s1)
    m = len(s2)
    if n == 0 and m == 0:
        return []
    if n == 0:
        return [
            AlignmentStep("INSERT", None, j, None, s2[j].timestamp, 1.0, 0.0, s2[j].audio_rms)
            for j in range(m)
        ]
    if m == 0:
        return [
            AlignmentStep("DELETE", i, None, s1[i].timestamp, None, 1.0, s1[i].audio_rms, 0.0)
            for i in range(n)
        ]

    w = max(5, int(math.ceil(band_seconds / step)))
    INF = 1e9

    # dp[i, offset] where offset = (j - i) + w
    # Valid offset range: 0 .. 2*w
    band_width = 2 * w + 1
    dp = np.full((n + 1, band_width), INF, dtype=np.float32)
    back_action = np.zeros((n + 1, band_width), dtype=np.int8)
    # actions: 1=diag(match/sub), 2=del(s1 advance), 3=ins(s2 advance)

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
                # offset in next row: (j+1) - (i+1) + w = j - i + w = k
                d = float(np.mean(np.abs(s1[i].thumb - s2[j].thumb)))
                cost = cur + min(d, DP_SUB_CAP)
                if cost < dp[i + 1, k]:
                    dp[i + 1, k] = cost
                    back_action[i + 1, k] = 1

            # 2. Deletion in s1: (i -> i+1, j)
            if i < n:
                # offset in next row: j - (i+1) + w = k - 1
                next_k = k - 1
                if 0 <= next_k < band_width:
                    cost = cur + DP_GAP_COST
                    if cost < dp[i + 1, next_k]:
                        dp[i + 1, next_k] = cost
                        back_action[i + 1, next_k] = 2

            # 3. Insertion in s2: (i, j -> j+1)
            if j < m:
                # offset in same row: (j+1) - i + w = k + 1
                next_k = k + 1
                if 0 <= next_k < band_width:
                    cost = cur + DP_GAP_COST
                    if cost < dp[i, next_k]:
                        dp[i, next_k] = cost
                        back_action[i, next_k] = 3

    # Traceback from (n, m)
    curr_i = n
    curr_k = (m - n) + w
    if curr_k < 0 or curr_k >= band_width or dp[curr_i, curr_k] >= INF:
        # Fallback to closest valid cell at row n
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
                a2=0.0,
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
                a1=0.0,
                a2=s2[prev_j].audio_rms,
            ))
            curr_k = prev_k
        else:
            # Reached beginning or boundary break
            break

    path.reverse()
    return path


@dataclass
class CandidateRegion:
    kind: str                      # "VISUAL", "TIMING_DELETE", "TIMING_INSERT", "AUDIO"
    t1_start: float | None
    t1_end: float | None
    t2_start: float | None
    t2_end: float | None
    steps: list[AlignmentStep]


def coalesce_candidate_regions(path: list[AlignmentStep], step: float) -> list[CandidateRegion]:
    """
    Coalesces consecutive alignment anomaly steps into candidate regions.
    Bridges tiny single-step flickers.
    """
    if not path:
        return []

    # First, tag steps with tentative anomaly category
    tagged: list[str] = []
    for s in path:
        if s.kind == "DELETE":
            tagged.append("TIMING_DELETE")
        elif s.kind == "INSERT":
            tagged.append("TIMING_INSERT")
        elif s.kind == "REPLACE":
            tagged.append("VISUAL")
        elif s.kind == "MATCH":
            # Check if there is an audio difference on visually matched frames
            a1, a2 = s.a1, s.a2
            is_mute = (a1 >= AUDIO_ACTIVE_MIN and a2 <= AUDIO_SILENT_MAX and (a2 / max(a1, 1e-6)) <= AUDIO_MUTE_DROP_RATIO)
            is_unmute = (a1 <= AUDIO_SILENT_MAX and a2 >= AUDIO_ACTIVE_MIN)
            major_shift = (max(a1, a2) >= AUDIO_ACTIVE_MIN and abs(a1 - a2) / max(a1, a2) >= AUDIO_SHIFT_RATIO)
            if is_mute or is_unmute or major_shift:
                tagged.append("AUDIO")
            else:
                tagged.append("NONE")
        else:
            tagged.append("NONE")

    # Bridge single-sample isolated "NONE" between identical non-NONE tags
    smoothed = list(tagged)
    for i in range(1, len(smoothed) - 1):
        if smoothed[i] == "NONE" and smoothed[i - 1] == smoothed[i + 1] and smoothed[i - 1] != "NONE":
            smoothed[i] = smoothed[i - 1]

    # Group consecutive identical tags
    regions: list[CandidateRegion] = []
    current_tag = "NONE"
    current_steps: list[AlignmentStep] = []

    for tag, step_item in zip(smoothed, path):
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
                    steps=current_steps,
                ))
            current_tag = tag
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
            steps=current_steps,
        ))

    return regions


def classify_and_verify_changes(
    regions: list[CandidateRegion],
    v1_path: Path,
    v2_path: Path,
    evidence_dir: Path,
    d1: float,
    d2: float,
) -> list[DetectedChange]:
    """
    Confirms candidate regions using full frame extraction, deterministic measurements,
    conservative reason codes, and creates evidence JPGs only for confirmed changes.
    """
    detected: list[DetectedChange] = []

    for idx, reg in enumerate(regions):
        change_id = f"change-{idx + 1:03d}"

        if reg.kind == "VISUAL":
            # Representative midpoint
            t1_mid = (reg.t1_start + reg.t1_end) / 2 if (reg.t1_start is not None and reg.t1_end is not None) else (reg.t1_start or 0.0)
            t2_mid = (reg.t2_start + reg.t2_end) / 2 if (reg.t2_start is not None and reg.t2_end is not None) else (reg.t2_start or 0.0)

            # High-resolution verification
            mean_abs, match_ratio = visual_difference_at(v1_path, t1_mid, v2_path, t2_mid)

            # Check if this is merely compression/encoding noise
            if mean_abs <= NOISE_DIFF_MAX and match_ratio >= NOISE_ORB_MATCH_MIN:
                continue
            if mean_abs < VISUAL_CHANGE_MIN:
                continue

            # Confirmed VISUAL change -> generate evidence frames
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

        elif reg.kind == "TIMING_DELETE":
            # Material removed from pre_final
            if reg.t1_start is None or reg.t1_end is None:
                continue
            removed_sec = max(0.0, reg.t1_end - reg.t1_start)
            if removed_sec < 0.2:
                # Negligible duration
                continue

            t1_mid = (reg.t1_start + reg.t1_end) / 2
            # Anchor in final
            final_anchor = reg.t2_start if reg.t2_start is not None else min(t1_mid, d2 - 0.05)

            p1_img = extract_frame(v1_path, t1_mid, evidence_dir / f"{change_id}-pre.jpg")
            p2_img = extract_frame(v2_path, final_anchor, evidence_dir / f"{change_id}-final.jpg")

            metrics = [
                EvidenceMetric(name="removed_duration_seconds", v1=round(removed_sec, 3), v2=0.0, delta=round(-removed_sec, 3), unit="seconds"),
            ]

            evidence = ChangeEvidence(
                pre_final_timestamp_seconds=round(t1_mid, 3),
                final_timestamp_seconds=round(final_anchor, 3),
                window_start_pre_final=reg.t1_start,
                window_end_pre_final=reg.t1_end,
                window_start_final=round(final_anchor, 3),
                window_end_final=round(final_anchor, 3),
                pre_final_frame_path=f"/evidence/{evidence_dir.name}/{p1_img.name}",
                final_frame_path=f"/evidence/{evidence_dir.name}/{p2_img.name}",
                metrics=metrics,
                methods=["bounded_sequence_alignment", "temporal_anchor_verification"],
                reason_codes=["segment_removed"],
                explanation=f"Approximately {removed_sec:.1f} seconds of material was removed from this region.",
            )

            detected.append(DetectedChange(
                id=change_id,
                kind=ChangeKind.TIMING,
                confidence=ChangeConfidence.HIGH,
                title="TIMING CHANGE",
                description=f"Approximately {removed_sec:.1f} seconds of material was removed from this region.",
                evidence=evidence,
            ))

        elif reg.kind == "TIMING_INSERT":
            # Material inserted into final
            if reg.t2_start is None or reg.t2_end is None:
                continue
            inserted_sec = max(0.0, reg.t2_end - reg.t2_start)
            if inserted_sec < 0.2:
                continue

            t2_mid = (reg.t2_start + reg.t2_end) / 2
            pre_anchor = reg.t1_start if reg.t1_start is not None else min(t2_mid, d1 - 0.05)

            p1_img = extract_frame(v1_path, pre_anchor, evidence_dir / f"{change_id}-pre.jpg")
            p2_img = extract_frame(v2_path, t2_mid, evidence_dir / f"{change_id}-final.jpg")

            metrics = [
                EvidenceMetric(name="inserted_duration_seconds", v1=0.0, v2=round(inserted_sec, 3), delta=round(inserted_sec, 3), unit="seconds"),
            ]

            evidence = ChangeEvidence(
                pre_final_timestamp_seconds=round(pre_anchor, 3),
                final_timestamp_seconds=round(t2_mid, 3),
                window_start_pre_final=round(pre_anchor, 3),
                window_end_pre_final=round(pre_anchor, 3),
                window_start_final=reg.t2_start,
                window_end_final=reg.t2_end,
                pre_final_frame_path=f"/evidence/{evidence_dir.name}/{p1_img.name}",
                final_frame_path=f"/evidence/{evidence_dir.name}/{p2_img.name}",
                metrics=metrics,
                methods=["bounded_sequence_alignment", "temporal_anchor_verification"],
                reason_codes=["segment_inserted"],
                explanation=f"Approximately {inserted_sec:.1f} seconds of material was inserted into this region.",
            )

            detected.append(DetectedChange(
                id=change_id,
                kind=ChangeKind.TIMING,
                confidence=ChangeConfidence.HIGH,
                title="TIMING CHANGE",
                description=f"Approximately {inserted_sec:.1f} seconds of material was inserted into this region.",
                evidence=evidence,
            ))

        elif reg.kind == "AUDIO":
            t1_mid = (reg.t1_start + reg.t1_end) / 2 if (reg.t1_start is not None and reg.t1_end is not None) else (reg.t1_start or 0.0)
            t2_mid = (reg.t2_start + reg.t2_end) / 2 if (reg.t2_start is not None and reg.t2_end is not None) else (reg.t2_start or 0.0)

            # Measure accurate RMS in the window
            win = max(0.5, (reg.t1_end or t1_mid) - (reg.t1_start or t1_mid))
            a1 = audio_rms(v1_path, t1_mid, window=win) if has_audio(v1_path) else 0.0
            a2 = audio_rms(v2_path, t2_mid, window=win) if has_audio(v2_path) else 0.0

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
                # Sub-threshold difference
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
    Validates media, samples visual/audio descriptors, runs bounded DP alignment,
    coalesces candidate change regions, and produces an evidence-first DiscoverResponse.
    """
    probe_media(pre_final_path)
    probe_media(final_path)

    d1 = duration_seconds(pre_final_path)
    d2 = duration_seconds(final_path)

    # Adaptive sample interval (0.5s for normal videos; scaled up for very long videos to bound to MAX_SAMPLES)
    max_dur = max(d1, d2)
    step = 0.5 if max_dur <= 300.0 else max(0.5, max_dur / 600.0)

    s1 = sample_video(pre_final_path, step=step)
    s2 = sample_video(final_path, step=step)

    alignment_path = align_sequences_banded(s1, s2, step=step)
    candidate_regions = coalesce_candidate_regions(alignment_path, step=step)
    changes = classify_and_verify_changes(
        candidate_regions,
        pre_final_path,
        final_path,
        evidence_dir,
        d1=d1,
        d2=d2,
    )

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
