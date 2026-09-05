from __future__ import annotations

import re
import uuid
from .models import CheckKind, RevisionRequest

_TS = re.compile(r"(?:(?P<h>\d{1,2}):)?(?P<m>\d{1,2}):(?P<s>\d{2})(?:\.(?P<ms>\d+))?|(?P<secs>\d+(?:\.\d+)?)\s*s\b", re.I)


def _timestamp_seconds(text: str) -> float | None:
    match = _TS.search(text)
    if not match:
        return None
    if match.group("secs"):
        return float(match.group("secs"))
    h = int(match.group("h") or 0)
    m = int(match.group("m") or 0)
    s = int(match.group("s") or 0)
    ms = float(f"0.{match.group('ms')}") if match.group("ms") else 0.0
    return h * 3600 + m * 60 + s + ms


def _kind(text: str) -> CheckKind:
    t = text.lower()
    if any(k in t for k in ("mute", "silence", "remove audio", "no audio")):
        return CheckKind.MUTE_AUDIO
    if any(k in t for k in ("pause", "dead air", "silence gap", "tighten")):
        return CheckKind.REMOVE_PAUSE
    if any(k in t for k in ("text", "title", "caption", "lower third", "spelling", "subtitle")):
        return CheckKind.TEXT_CHANGE
    if any(k in t for k in ("zoom", "crop", "punch in", "punch-in", "reframe")):
        return CheckKind.ZOOM_CROP
    if any(k in t for k in ("replace shot", "b-roll", "broll", "color", "blur", "logo", "graphic")):
        return CheckKind.VISUAL_CHANGE
    return CheckKind.GENERIC


def parse_notes(notes: str) -> list[RevisionRequest]:
    lines = [line.strip(" \t-*•") for line in notes.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return []
    requests: list[RevisionRequest] = []
    for line in lines:
        requests.append(
            RevisionRequest(
                id=uuid.uuid4().hex[:10],
                raw_text=line,
                kind=_kind(line),
                timestamp_seconds=_timestamp_seconds(line),
                expected=line,
            )
        )
    return requests
