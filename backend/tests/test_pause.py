from pathlib import Path
import subprocess
import numpy as np
import pytest
from app import pause


def test_fixture_local_pause(sample):
    v1, v2 = sample/'demo-v1.mp4', sample/'demo-v2.mp4'
    verdict, _, _, signals = pause.check_pause(v1, v2, 10.5)
    assert verdict == 'PASS'
    assert signals['removed_seconds'] == pytest.approx(1, abs=.11)
    assert pause.check_pause(v1, v1, 10.5)[0] == 'FAIL'


def test_shorter_export_elsewhere_does_not_pass(sample, tmp_path):
    v1 = sample/'demo-v1.mp4'
    shortened = tmp_path/'shorter.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(v1),'-t','13','-c','copy',str(shortened)], check=True)
    assert pause.check_pause(v1, shortened, 10.5)[0] == 'FAIL'


@pytest.mark.parametrize('mode,expected', [('no_audio','REVIEW'), ('active','REVIEW'),
    ('unbounded','REVIEW'), ('ambiguous','REVIEW'), ('weak','REVIEW'), ('wrong_alignment','REVIEW')])
def test_pause_uncertainty(monkeypatch, mode, expected):
    monkeypatch.setattr(pause, 'has_audio', lambda _: mode != 'no_audio')
    monkeypatch.setattr(pause, 'duration_seconds', lambda _: 20)
    env = np.full(60, .1)
    env[25:36] = 0
    if mode == 'active':
        env[:] = .1
    if mode == 'unbounded':
        env[:] = 0
    if mode == 'weak':
        env[22:25] = .005
    monkeypatch.setattr(pause, 'audio_envelope', lambda *args: env)
    monkeypatch.setattr(pause, '_anchor', lambda *args: (0, .2 if mode == 'wrong_alignment' else .001,
                                                       0 if mode == 'ambiguous' else .1))
    assert pause.check_pause(Path('a'), Path('b'), 5)[0] == expected
