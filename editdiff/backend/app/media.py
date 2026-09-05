from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
import cv2
import numpy as np


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, capture_output=True, timeout=60)


class MediaError(ValueError):
    """Invalid or undecodable media (safe message supplied at API boundary)."""


def probe_media(path: Path) -> dict:
    data = json.loads(_run([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)
    ]).stdout)
    try:
        duration = float(data.get("format", {}).get("duration", 0))
    except (TypeError, ValueError) as exc:
        raise MediaError("Invalid media duration.") from exc
    videos = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    if not videos or not math.isfinite(duration) or not 0.2 <= duration <= 1800:
        raise MediaError("Video duration must be between 0.2 and 1800 seconds.")
    if any(s.get("width", 0) * s.get("height", 0) > 3840 * 2160 for s in videos):
        raise MediaError("Video exceeds supported resolution.")
    return data


def has_audio(path: Path) -> bool:
    return any(s.get("codec_type") == "audio" for s in probe_media(path)["streams"])


def duration_seconds(path: Path) -> float:
    cp = _run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(path)
    ])
    data = json.loads(cp.stdout)
    return float(data["format"]["duration"])


def extract_frame(path: Path, timestamp: float, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _run([
        "ffmpeg", "-y", "-ss", f"{max(timestamp, 0):.3f}", "-i", str(path),
        "-frames:v", "1", "-vf", "scale=960:-2", str(out_path)
    ])
    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise MediaError("Frame extraction failed.")
    return out_path


def frame_gray(path: Path, timestamp: float) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_MSEC, max(timestamp, 0) * 1000)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise MediaError("Could not decode requested frame.")
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, (480, 270), interpolation=cv2.INTER_AREA)


def visual_difference(path1: Path, path2: Path, timestamp: float) -> tuple[float, float]:
    a = frame_gray(path1, timestamp)
    b = frame_gray(path2, timestamp)
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


def audio_rms(path: Path, timestamp: float, window: float = 1.5, sample_rate: int = 16000) -> float:
    start = max(timestamp - window / 2, 0)
    cp = subprocess.run([
        "ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{window:.3f}",
        "-i", str(path), "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-f", "s16le", "pipe:1"
    ], check=True, capture_output=True, timeout=60)
    if not cp.stdout:
        raise MediaError("No audio samples decoded in the requested window.")
    samples = np.frombuffer(cp.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    if samples.size == 0:
        raise MediaError("No audio samples decoded in the requested window.")
    return float(math.sqrt(float(np.mean(samples * samples))))


def audio_envelope(path: Path, start: float, length: float, step: float = 0.1) -> np.ndarray:
    """RMS bins, with incomplete final bins discarded rather than padded silent."""
    cp = _run(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{length:.3f}",
               "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "pipe:1"])
    samples = np.frombuffer(cp.stdout, np.int16).astype(np.float32) / 32768
    size = round(16000 * step)
    samples = samples[:len(samples) // size * size]
    return np.sqrt(np.mean(samples.reshape(-1, size) ** 2, axis=1)) if len(samples) else np.array([])
