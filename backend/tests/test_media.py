import subprocess
from types import SimpleNamespace
import pytest
from app import media


def test_no_audio_samples_are_not_silence(monkeypatch, tmp_path):
    monkeypatch.setattr(media.subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(stdout=b''))
    with pytest.raises(media.MediaError):
        media.audio_rms(tmp_path/'empty.mp4', 1)


@pytest.mark.parametrize('duration,streams', [
    ('NaN', [{'codec_type':'video'}]), ('N/A', [{'codec_type':'video'}]),
    ('0', [{'codec_type':'video'}]), ('1801', [{'codec_type':'video'}]),
    ('10', [{'codec_type':'audio'}]),
    ('10', [{'codec_type':'video','width':8000,'height':8000}]),
])
def test_invalid_media_metadata(monkeypatch, tmp_path, duration, streams):
    import json
    monkeypatch.setattr(media, '_run', lambda _: SimpleNamespace(stdout=json.dumps(
        {'format': {'duration':duration}, 'streams':streams})))
    with pytest.raises(media.MediaError):
        media.probe_media(tmp_path/'video')


def test_audio_track_removal_and_absent_source(client, sample, tmp_path):
    target = tmp_path/'no-audio.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(sample/'demo-v1.mp4'),
                    '-an','-c:v','copy',str(target)], check=True)
    source = (sample/'demo-v1.mp4').read_bytes()
    silent = target.read_bytes()
    for before, after, expected in ((source,silent,'PASS'),(silent,silent,'REVIEW')):
        response = client.post('/analyze', files={'v1':('a.mp4',before),'v2':('b.mp4',after)},
                               data={'notes':'1.5s mute audio'})
        assert response.status_code == 200
        assert response.json()['results'][0]['verdict'] == expected
