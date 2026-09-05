from app.models import CheckKind
from app.notes import parse_notes


def test_parse_timestamps_and_kinds():
    notes = """
    - 00:12 mute the background audio
    - 0:24 change title text to Final Cut
    - 35s punch in 15%
    - 00:48 remove the long pause
    """
    result = parse_notes(notes)
    assert [x.kind for x in result] == [
        CheckKind.MUTE_AUDIO,
        CheckKind.TEXT_CHANGE,
        CheckKind.ZOOM_CROP,
        CheckKind.REMOVE_PAUSE,
    ]
    assert [x.timestamp_seconds for x in result] == [12.0, 24.0, 35.0, 48.0]
