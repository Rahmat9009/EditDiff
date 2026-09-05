import json
import pytest
from app import main, verifier
from app.models import AnalyzeResponse
from app.semantic import SemanticFinding


def upload(sample, notes=None):
    return dict(files={'v1': ('v1.mp4', (sample/'demo-v1.mp4').read_bytes(), 'video/mp4'),
                       'v2': ('v2.mp4', (sample/'demo-v2.mp4').read_bytes(), 'video/mp4')},
                data={'notes': notes or (sample/'edit-notes.txt').read_text()})


def test_real_api_report_persistence_and_evidence(client, sample):
    response = client.post('/analyze', **upload(sample))
    assert response.status_code == 200, response.text
    report = response.json()
    spec = json.loads((sample/'golden-demo.json').read_text())
    assert report['summary'] == spec['expected_summary']
    assert [r['verdict'] for r in report['results']] == [r['expected_verdict'] for r in spec['revisions']]
    assert set(report) >= {'report_id', 'summary', 'results'}
    for result in report['results']:
        assert set(result) >= {'request', 'verdict', 'confidence', 'evidence'}
        assert 0 <= result['confidence'] <= .9
        evidence = result['evidence']
        assert set(evidence) >= {'timestamp_seconds', 'v1_frame_path', 'v2_frame_path', 'metrics', 'explanation'}
        assert evidence['methods'] and evidence['reason_codes']
        for frame in evidence['frames']:
            assert frame['path'].startswith('/evidence/' + report['report_id'] + '/')
            image = client.get(frame['path'])
            assert image.status_code == 200
            assert image.headers['content-type'] == 'image/jpeg'
    assert ':\\' not in response.text
    report_id = report['report_id']
    assert client.get(f'/reports/{report_id}').json() == report
    exported = client.get(f'/reports/{report_id}/export')
    assert exported.json() == report
    assert exported.headers['content-type'] == 'application/json'
    assert exported.headers['content-disposition'] == f'attachment; filename="editdiff-{report_id}.json"'
    # Disk is the source of truth; no process-local report cache is needed.
    stored = main.REPORTS / f'{report_id}.json'
    assert AnalyzeResponse.model_validate_json(stored.read_text()).model_dump(mode='json') == report
    assert list(main.UPLOADS.iterdir()) == []


def test_semantic_window_integration(client, sample, monkeypatch):
    def semantic(req, frames):
        assert [t for t, _, _ in frames] == [3.5, 4, 4.5]
        assert all(before.is_file() and after.is_file() for _, before, after in frames)
        return SemanticFinding(verdict='PASS', confidence=.96, before_observation='DRAFT CUT',
            after_observation='LAUNCH DAY', after_state_confirmed=True, observed_after_text='LAUNCH DAY',
            supporting_frame_indices=[0,1,2]), 'available'
    monkeypatch.setattr(verifier, 'verify_semantic', semantic)
    response = client.post('/analyze', **upload(sample, '00:04 change title from "DRAFT CUT" to "LAUNCH DAY"'))
    assert response.status_code == 200
    result = response.json()['results'][0]
    assert result['verdict'] == 'PASS'
    assert result['confidence'] == .88
    assert result['evidence']['semantic_status'] == 'available'


@pytest.mark.parametrize('files,data,status', [
    ({}, {'notes':'mute'}, 422),
    ({'v1':('a',b'bad')}, {'notes':'mute'}, 422),
    ({'v1':('a',b''),'v2':('b',b'bad')}, {'notes':'3s mute'}, 400),
    ({'v1':('a',b'bad'),'v2':('b',b'bad')}, {'notes':'3s mute'}, 422),
    ({'v1':('a',b'bad'),'v2':('b',b'bad')}, {'notes':'   '}, 400),
    ({'v1':('a',b'bad'),'v2':('b',b'bad')}, {'notes':'x'*20001}, 400),
    ({'v1':('a',b'bad'),'v2':('b',b'bad')}, {'notes':'mute\n'*31}, 400),
])
def test_invalid_uploads(client, files, data, status):
    response = client.post('/analyze', files=files, data=data)
    assert response.status_code == status
    assert ':\\' not in response.text
    assert list(main.UPLOADS.iterdir()) == []
    assert list(main.EVIDENCE.iterdir()) == []
    assert list(main.REPORTS.iterdir()) == []


def test_upload_limit(client, monkeypatch):
    monkeypatch.setattr(main, 'MAX_UPLOAD_BYTES', 2)
    response = client.post('/analyze', files={'v1':('a',b'123'),'v2':('b',b'123')},data={'notes':'mute'})
    assert response.status_code == 413
    assert list(main.UPLOADS.iterdir()) == []


@pytest.mark.parametrize('report_id', ['missing', 'abcdef123456', '..', 'ABCDEF123456'])
def test_missing_reports(client, report_id):
    assert client.get(f'/reports/{report_id}').status_code == 404
    assert client.get(f'/reports/{report_id}/export').status_code == 404


def test_unlocated_notes_do_not_check_substitute_frames(client, sample):
    response = client.post('/analyze', **upload(sample, 'mute\n99s change title'))
    assert response.status_code == 200
    assert all(r['verdict'] == 'REVIEW' and not r['evidence']['frames'] for r in response.json()['results'])


def test_programming_errors_are_not_disguised_as_invalid_media(client, sample, monkeypatch):
    def broken(*args):
        raise RuntimeError('programming error')
    monkeypatch.setattr(main, 'verify', broken)
    with pytest.raises(RuntimeError, match='programming error'):
        client.post('/analyze', **upload(sample, '1s mute'))
    assert list(main.UPLOADS.iterdir()) == []
    assert list(main.EVIDENCE.iterdir()) == []
