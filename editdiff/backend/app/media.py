from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
import cv2
import numpy as np


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, check=True, capture_output=True)


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
    return out_path


def frame_gray(path: Path, timestamp: float) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_MSEC, max(timestamp, 0) * 1000)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        raise RuntimeError(f"Could not read frame at {timestamp}s from {path.name}")
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
    ], check=True, capture_output=True)
    if not cp.stdout:
        return 0.0
    samples = np.frombuffer(cp.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    if samples.size == 0:
        return 0.0
    return float(math.sqrt(float(np.mean(samples * samples))))
