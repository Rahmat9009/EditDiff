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
    if s >= 60 or (match.group("h") and m >= 60):
        return None
    ms = float(f"0.{match.group('ms')}") if match.group("ms") else 0.0
    return h * 3600 + m * 60 + s + ms


def _kind(text: str) -> CheckKind:
    t = text.lower()
    if any(k in t for k in ("pause", "dead air", "silence gap", "tighten")):
        return CheckKind.REMOVE_PAUSE
    if any(k in t for k in ("mute", "silence", "remove audio", "no audio")):
        return CheckKind.MUTE_AUDIO
    if any(k in t for k in ("text", "title", "caption", "lower third", "spelling", "subtitle")):
        return CheckKind.TEXT_CHANGE
    if any(k in t for k in ("zoom", "crop", "punch in", "punch-in", "reframe")):
        return CheckKind.ZOOM_CROP
    if any(k in t for k in ("replace shot", "b-roll", "broll", "color", "blur", "logo", "graphic")):
        return CheckKind.VISUAL_CHANGE
    return CheckKind.GENERIC


def expected_text(text: str) -> tuple[str | None, str | None]:
    """Extract explicit quoted wording; never invent an unquoted target."""
    quotes = r'[\"\u201c\u2018\x27]([^\"\u201d\u2019\x27]+)[\"\u201d\u2019\x27]'
    replacement = re.search(r'from\s+' + quotes + r'\s+to\s+' + quotes, text, re.I)
    if replacement:
        return replacement.group(1), replacement.group(2)
    target = re.search(r'(?:to|with|say|read)\s+' + quotes, text, re.I)
    return (None, target.group(1)) if target else (None, None)


def parse_notes(notes: str) -> list[RevisionRequest]:
    lines = [line.strip(" \t-*•") for line in notes.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return []
    requests: list[RevisionRequest] = []
    for line in lines:
        old, new = expected_text(line) if _kind(line) == CheckKind.TEXT_CHANGE else (None, None)
        requests.append(
            RevisionRequest(
                id=uuid.uuid4().hex[:10],
                raw_text=line,
                kind=_kind(line),
                timestamp_seconds=_timestamp_seconds(line),
                expected=line,
                expected_old_text=old,
                expected_new_text=new,
            )
        )
    return requests
