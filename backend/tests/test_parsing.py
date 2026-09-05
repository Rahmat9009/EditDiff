import pytest
from app.notes import parse_notes, expected_text
from app.models import CheckKind


@pytest.mark.parametrize('note,kind', [
    ('00:03 remove the silence gap', CheckKind.REMOVE_PAUSE),
    ('00:05 Punch in 20%', CheckKind.ZOOM_CROP),
    ('Replace the B-roll at 00:07 with the city shot', CheckKind.VISUAL_CHANGE),
    ('Remove the logo at 00:08', CheckKind.VISUAL_CHANGE),
    ('Blur the license plate at 00:09', CheckKind.VISUAL_CHANGE),
    ('make it better', CheckKind.GENERIC),
])
def test_intents(note, kind):
    assert parse_notes(note)[0].kind == kind


@pytest.mark.parametrize('note,old,new', [
    ('Change title from “DRAFT CUT” to “LAUNCH DAY”.', 'DRAFT CUT', 'LAUNCH DAY'),
    ("Change title from 'DRAFT CUT' to 'LAUNCH DAY'.", 'DRAFT CUT', 'LAUNCH DAY'),
    ('Set title to "Launch day!"', None, 'Launch day!'),
    ('Change title to something better', None, None),
])
def test_expected_text(note, old, new):
    assert expected_text(note) == (old, new)
    request = parse_notes(note)[0]
    assert (request.expected_old_text, request.expected_new_text) == (old, new)
    assert request.expected == note


def test_empty_and_fractional_timestamp():
    assert parse_notes(' \n- ') == []
    assert parse_notes('01:02:03.5 mute')[0].timestamp_seconds == 3723.5
    assert parse_notes('1.5s mute')[0].timestamp_seconds == 1.5
    assert parse_notes('mute')[0].timestamp_seconds is None
