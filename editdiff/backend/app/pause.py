"""Local silence plus independently matched visual anchors around a suspected cut."""
from pathlib import Path

import numpy as np

from .media import audio_envelope, duration_seconds, frame_gray, has_audio

THRESHOLDS = {"silence_rms": 0.004, "active_rms": 0.008, "minimum_cut_seconds": 0.3,
              "anchor_error_max": 0.035, "anchor_margin_min": 0.008, "offset_search_seconds": 2.5}


def _anchor(v1: Path, v2: Path, t: float, duration: float) -> tuple[float, float, float]:
    source = [frame_gray(v1, t + dt).astype(float) for dt in (-0.1, 0.1)]
    candidates = []
    for offset in np.arange(-2.5, 2.51, 0.1):
        if t + offset - 0.1 < 0 or t + offset + 0.1 >= duration - 0.05:
            continue
        error = np.mean([np.mean(np.abs(a - frame_gray(v2, t + offset + dt))) / 255
                         for a, dt in zip(source, (-0.1, 0.1))])
        candidates.append((float(error), float(offset)))
    if not candidates:
        return 0.0, 1.0, 0.0
    error, offset = min(candidates)
    alternatives = [e for e, o in candidates if abs(o - offset) > 0.3]
    margin = min(alternatives, default=error) - error
    return offset, error, margin


def check_pause(v1: Path, v2: Path, ts: float) -> tuple[str, float, str, dict[str, float]]:
    signals: dict[str, float] = {}
    if not has_audio(v1) or not has_audio(v2):
        return "REVIEW", 0.35, "pause_audio_unavailable", signals
    start = max(0, ts - 3)
    env = audio_envelope(v1, start, min(6, duration_seconds(v1) - start))
    center = round((ts - start) / 0.1)
    if center >= len(env) or env[center] >= THRESHOLDS["silence_rms"]:
        return "REVIEW", 0.4, "no_local_silence_at_timestamp", signals
    left = right = center
    while left > 0 and env[left - 1] < THRESHOLDS["silence_rms"]:
        left -= 1
    while right + 1 < len(env) and env[right + 1] < THRESHOLDS["silence_rms"]:
        right += 1
    if left < 3 or right + 4 >= len(env):
        return "REVIEW", 0.4, "pause_not_bounded", signals
    if min(np.mean(env[left-3:left]), np.mean(env[right+1:right+4])) < THRESHOLDS["active_rms"]:
        return "REVIEW", 0.4, "weak_pause_flanks", signals
    gap_start, gap_end = start + left * 0.1, start + (right + 1) * 0.1
    before, after = gap_start - 0.25, gap_end + 0.25
    d2 = duration_seconds(v2)
    pre, e1, m1 = _anchor(v1, v2, before, d2)
    post, e2, m2 = _anchor(v1, v2, after, d2)
    cut = pre - post
    signals.update(pause_start=gap_start, pause_end=gap_end, pre_anchor_time=before,
                   post_anchor_time=after, pre_offset=pre, post_offset=post,
                   removed_seconds=cut, pre_anchor_error=e1, post_anchor_error=e2,
                   pre_anchor_margin=m1, post_anchor_margin=m2)
    if max(e1, e2) > THRESHOLDS["anchor_error_max"] or min(m1, m2) < THRESHOLDS["anchor_margin_min"]:
        return "REVIEW", 0.45, "ambiguous_temporal_anchors", signals
    v2_start, v2_end = gap_start + pre, gap_end + post
    if v2_start < 0 or v2_end > d2 or v2_end < v2_start - 0.15:
        return "REVIEW", 0.4, "inconsistent_local_alignment", signals
    remaining = audio_envelope(v2, max(0, v2_start), max(0.1, v2_end - v2_start))
    if not len(remaining):
        return "REVIEW", 0.35, "aligned_audio_unavailable", signals
    silent = float(np.sum(remaining < THRESHOLDS["silence_rms"]) * 0.1)
    signals["v2_remaining_silence"] = silent
    if 0.3 <= cut <= gap_end - gap_start + 0.15 and silent <= (gap_end - gap_start) - 0.3:
        return "PASS", 0.86, "local_silence_removed_with_aligned_flanks", signals
    if abs(cut) < 0.15 and silent >= gap_end - gap_start - 0.2:
        return "FAIL", 0.84, "local_pause_retained", signals
    return "REVIEW", 0.45, "local_signals_inconclusive", signals
