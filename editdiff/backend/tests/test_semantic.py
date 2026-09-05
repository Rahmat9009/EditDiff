import json
from pathlib import Path
import pytest
from app import semantic
from app.semantic import SemanticFinding
from app.verifier import fuse_visual, check_mute
from app.notes import parse_notes


def finding(**changes):
    values = dict(verdict='PASS', confidence=.95, before_observation='DRAFT CUT is visible',
                  after_observation='LAUNCH DAY is visible', after_state_confirmed=True,
                  observed_after_text='LAUNCH DAY', supporting_frame_indices=[0, 1, 2])
    values.update(changes)
    return SemanticFinding(**values)


@pytest.mark.parametrize('deltas,result,expected', [
    ([.2]*3, None, 'REVIEW'),
    ([0]*3, None, 'FAIL'),
    ([0]*3, finding(), 'REVIEW'),
    ([.03]*3, finding(), 'PASS'),
    ([.03]*3, finding(observed_after_text='WRONG WORDS'), 'REVIEW'),
    ([.03]*3, finding(after_state_confirmed=False), 'REVIEW'),
    ([.03]*3, finding(confidence=.4), 'REVIEW'),
    ([.03]*3, finding(verdict='FAIL', after_state_confirmed=False), 'FAIL'),
    ([.03]*3, finding(verdict='FAIL'), 'REVIEW'),
    ([.03]*3, finding(verdict='REVIEW'), 'REVIEW'),
    ([.03,0,0], finding(supporting_frame_indices=[1]), 'REVIEW'),
])
def test_text_fusion(deltas, result, expected):
    req = parse_notes('00:03 Change title from "DRAFT CUT" to "LAUNCH DAY"')[0]
    verdict, confidence, _, _ = fuse_visual(req, deltas, result)
    assert verdict == expected
    assert 0 <= confidence <= .88


def test_unknown_target_and_exact_crop():
    for note in ('00:03 change title', '00:03 punch in 20%'):
        assert fuse_visual(parse_notes(note)[0], [.1]*3, finding())[0] == 'REVIEW'
    assert fuse_visual(parse_notes('00:03 crop tighter')[0], [.1]*3, finding())[0] == 'PASS'


@pytest.mark.parametrize('before,after,expected', [
    (.1,0,'PASS'), (.1,.02,'REVIEW'), (.1,.08,'FAIL'), (0,0,'REVIEW'),
    (.003,.001,'REVIEW'), (.1,.003,'PASS'), (.1,.05,'REVIEW'),
])
def test_mute(before, after, expected):
    verdict, confidence, _ = check_mute(before, after)
    assert verdict == expected
    assert 0 <= confidence <= .9


@pytest.mark.parametrize('response', [
    '{}', 'not JSON', '{"verdict":"PASS"}',
    json.dumps(finding().model_dump() | {'confidence': 1.1}),
    json.dumps(finding().model_dump() | {'supporting_frame_indices': [3]}),
    json.dumps(finding().model_dump() | {'after_state_confirmed': 'true'}),
    json.dumps(finding().model_dump() | {'after_observation': 'test-secret-key'}),
])
def test_invalid_external_response(monkeypatch, response):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-secret-key')
    monkeypatch.setenv('GEMINI_MODEL', 'test-model')
    monkeypatch.setattr(semantic, '_generate', lambda *args: response)
    result, status = semantic.verify_semantic(parse_notes('3s change title')[0], [(3, Path('a'), Path('b'))]*3)
    assert result is None
    assert status != 'available'


@pytest.mark.parametrize('error', [TimeoutError('key'), RuntimeError('429 key'), ValueError('bad payload')])
def test_external_failure(monkeypatch, error):
    monkeypatch.setenv('GEMINI_API_KEY', 'test-secret-key')
    monkeypatch.setenv('GEMINI_MODEL', 'test-model')
    def fail(*args):
        raise error
    monkeypatch.setattr(semantic, '_generate', fail)
    assert semantic.verify_semantic(parse_notes('3s change title')[0], [])[0] is None


def test_missing_config_and_valid_response(monkeypatch):
    req = parse_notes('3s change title')[0]
    assert semantic.verify_semantic(req, []) == (None, 'missing_key')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-secret-key')
    assert semantic.verify_semantic(req, []) == (None, 'missing_model')
    monkeypatch.setenv('GEMINI_MODEL', 'test-model')
    monkeypatch.setattr(semantic, '_generate', lambda *args: finding().model_dump_json())
    assert semantic.verify_semantic(req, [(3, Path('a'), Path('b'))]*3)[1] == 'available'
