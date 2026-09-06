import subprocess
from pathlib import Path
import pytest
from app import discovery, main
from app.models import ChangeConfidence, ChangeKind, DiscoverResponse


def _create_synthetic_video(
    path: Path,
    duration: float = 4.0,
    color: str = "red",
    with_audio: bool = True,
    fps: int = 10,
    crf: int = 23,
) -> Path:
    cmd = [
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", f"color=c={color}:s=320x240:d={duration}:r={fps}",
    ]
    if with_audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}"]
    cmd += [
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf),
    ]
    if with_audio:
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    else:
        cmd += ["-an"]
    cmd.append(str(path))
    subprocess.run(cmd, check=True)
    return path


def test_discover_identical_media_zero_changes(client, tmp_path):
    v1 = _create_synthetic_video(tmp_path / "v1.mp4", duration=3.0, color="blue")
    response = client.post(
        "/discover",
        files={
            "pre_final": ("v1.mp4", v1.read_bytes(), "video/mp4"),
            "final": ("v2.mp4", v1.read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["summary"]["total_changes"] == 0
    assert len(data["changes"]) == 0
    assert data["duration_delta_seconds"] == pytest.approx(0.0, abs=0.05)


def test_discover_shot_replacement(client, tmp_path):
    # V1: 6 seconds of blue
    v1 = _create_synthetic_video(tmp_path / "v1.mp4", duration=6.0, color="blue")
    # V2: 6 seconds with green from 2.0 to 3.5
    v2 = tmp_path / "v2.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=6.0:r=10",
        "-f", "lavfi", "-i", "color=c=green:s=320x240:d=1.5:r=10",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=6.0",
        "-filter_complex", "[0:v][1:v]overlay=enable='between(t,2.0,3.5)'[outv]",
        "-map", "[outv]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(v2),
    ], check=True)

    response = client.post(
        "/discover",
        files={
            "pre_final": ("v1.mp4", v1.read_bytes(), "video/mp4"),
            "final": ("v2.mp4", v2.read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["summary"]["visual"] == 1
    assert data["summary"]["timing"] == 0
    change = data["changes"][0]
    assert change["kind"] == "VISUAL"
    assert change["title"] == "VISUAL CHANGE"
    assert change["confidence"] in ("HIGH", "MEDIUM")
    ev = change["evidence"]
    assert ev["pre_final_frame_path"] and ev["final_frame_path"]
    assert 1.5 <= ev["final_timestamp_seconds"] <= 4.0


def test_discover_removed_segment(client, tmp_path):
    # V1: 6s video (0-2s red, 2-3.5s yellow, 3.5-6s blue)
    v1 = tmp_path / "v1.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "color=c=red:s=320x240:d=2.0:r=10",
        "-f", "lavfi", "-i", "color=c=yellow:s=320x240:d=1.5:r=10",
        "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2.5:r=10",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=6.0",
        "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[outv]",
        "-map", "[outv]", "-map", "3:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(v1),
    ], check=True)

    # V2: 4.5s video (0-2s red, 2-4.5s blue) -> yellow 1.5s segment removed!
    v2 = tmp_path / "v2.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "color=c=red:s=320x240:d=2.0:r=10",
        "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2.5:r=10",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=4.5",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[outv]",
        "-map", "[outv]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(v2),
    ], check=True)

    response = client.post(
        "/discover",
        files={
            "pre_final": ("v1.mp4", v1.read_bytes(), "video/mp4"),
            "final": ("v2.mp4", v2.read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["summary"]["timing"] >= 1
    assert data["summary"]["visual"] == 0
    timing_change = next(c for c in data["changes"] if c["kind"] == "TIMING")
    assert "segment_removed_with_aligned_flanks" in timing_change["evidence"]["reason_codes"]
    assert "temporal_anchor_verification" in timing_change["evidence"]["methods"]
    assert timing_change["confidence"] == "HIGH"
    metrics_by_name = {m["name"]: m for m in timing_change["evidence"]["metrics"]}
    assert "pre_flank_visual_distance" in metrics_by_name
    assert "post_flank_visual_distance" in metrics_by_name
    assert "offset_before_seconds" in metrics_by_name
    assert "offset_after_seconds" in metrics_by_name
    assert "inferred_timing_delta_seconds" in metrics_by_name
    assert timing_change["evidence"]["explanation"].startswith("Approximately 1.5 seconds")


def test_discover_inserted_segment(client, tmp_path):
    # V1: 4.5s video (0-2s red, 2-4.5s blue)
    v1 = tmp_path / "v1.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "color=c=red:s=320x240:d=2.0:r=10",
        "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2.5:r=10",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=4.5",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[outv]",
        "-map", "[outv]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(v1),
    ], check=True)

    # V2: 6.0s video (0-2s red, 2-3.5s yellow inserted, 3.5-6s blue)
    v2 = tmp_path / "v2.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "color=c=red:s=320x240:d=2.0:r=10",
        "-f", "lavfi", "-i", "color=c=yellow:s=320x240:d=1.5:r=10",
        "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2.5:r=10",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=6.0",
        "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[outv]",
        "-map", "[outv]", "-map", "3:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(v2),
    ], check=True)

    response = client.post(
        "/discover",
        files={
            "pre_final": ("v1.mp4", v1.read_bytes(), "video/mp4"),
            "final": ("v2.mp4", v2.read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["summary"]["timing"] >= 1
    assert data["summary"]["visual"] == 0
    timing_change = next(c for c in data["changes"] if c["kind"] == "TIMING")
    assert "segment_inserted_with_aligned_flanks" in timing_change["evidence"]["reason_codes"]
    assert "temporal_anchor_verification" in timing_change["evidence"]["methods"]
    assert timing_change["confidence"] == "HIGH"
    assert timing_change["evidence"]["explanation"].startswith("Approximately 1.5 seconds")


def test_discover_adversarial_replacement_not_deletion_insertion(client, tmp_path):
    """
    Adversarial scenario: PRE: A | B | C | D | E, FINAL: A | B | X | D | E
    where C and X have equal duration (1.5s) but different visuals.
    Must produce a VISUAL change and NO high-confidence TIMING deletion/insertion pair.
    """
    # 5 scenes: 1s red, 1s green, 1.5s white, 1s blue, 1s black (total 5.5s)
    v1 = tmp_path / "v1.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "color=c=red:s=320x240:d=1.0:r=10",
        "-f", "lavfi", "-i", "color=c=green:s=320x240:d=1.0:r=10",
        "-f", "lavfi", "-i", "color=c=white:s=320x240:d=1.5:r=10",
        "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1.0:r=10",
        "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1.0:r=10",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5.5",
        "-filter_complex", "[0:v][1:v][2:v][3:v][4:v]concat=n=5:v=1:a=0[outv]",
        "-map", "[outv]", "-map", "5:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(v1),
    ], check=True)

    # V2: same except C (white) is replaced with X (yellow) of exact same 1.5s duration
    v2 = tmp_path / "v2.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "color=c=red:s=320x240:d=1.0:r=10",
        "-f", "lavfi", "-i", "color=c=green:s=320x240:d=1.0:r=10",
        "-f", "lavfi", "-i", "color=c=yellow:s=320x240:d=1.5:r=10",
        "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1.0:r=10",
        "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1.0:r=10",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=5.5",
        "-filter_complex", "[0:v][1:v][2:v][3:v][4:v]concat=n=5:v=1:a=0[outv]",
        "-map", "[outv]", "-map", "5:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(v2),
    ], check=True)

    response = client.post(
        "/discover",
        files={
            "pre_final": ("v1.mp4", v1.read_bytes(), "video/mp4"),
            "final": ("v2.mp4", v2.read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["summary"]["visual"] == 1
    # Must NOT produce high-confidence timing deletion or insertion pair
    high_timing = [c for c in data["changes"] if c["kind"] == "TIMING" and c["confidence"] == "HIGH"]
    assert len(high_timing) == 0


def test_discover_edge_timing_single_flank(client, tmp_path):
    """
    Edge edit: Delete 1.5s at the very beginning.
    PRE: A (1.5s red) | B (2s blue)
    FINAL: B (2s blue)
    Pre-flank does not exist at t=0; only post-flank exists.
    Must produce MEDIUM confidence and timing_change_single_flank.
    """
    v1 = tmp_path / "v1.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "color=c=red:s=320x240:d=1.5:r=10",
        "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=2.0:r=10",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3.5",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[outv]",
        "-map", "[outv]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(v1),
    ], check=True)

    v2 = _create_synthetic_video(tmp_path / "v2.mp4", duration=2.0, color="blue")

    response = client.post(
        "/discover",
        files={
            "pre_final": ("v1.mp4", v1.read_bytes(), "video/mp4"),
            "final": ("v2.mp4", v2.read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    timing_changes = [c for c in data["changes"] if c["kind"] == "TIMING"]
    assert len(timing_changes) >= 1
    edge_change = timing_changes[0]
    assert edge_change["confidence"] == "MEDIUM"
    assert "timing_change_single_flank" in edge_change["evidence"]["reason_codes"]
    assert "temporal_anchor_verification" not in edge_change["evidence"]["methods"]


def test_discover_audio_processing_failure_no_false_audio_change(client, tmp_path, monkeypatch):
    """
    Audio envelope/FFmpeg processing failure must become unavailable (None),
    and must never trigger local_audio_muted / local_audio_added / local_audio_energy_shifted.
    """
    v1 = _create_synthetic_video(tmp_path / "v1.mp4", duration=4.0, color="blue")
    v2 = _create_synthetic_video(tmp_path / "v2.mp4", duration=4.0, color="blue")

    def failing_audio_envelope(*args, **kwargs):
        raise RuntimeError("FFmpeg audio decode simulated failure")

    monkeypatch.setattr(discovery, "audio_envelope", failing_audio_envelope)

    response = client.post(
        "/discover",
        files={
            "pre_final": ("v1.mp4", v1.read_bytes(), "video/mp4"),
            "final": ("v2.mp4", v2.read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    # Identical videos with audio envelope failure: zero false audio changes
    assert data["summary"]["audio"] == 0
    assert data["summary"]["total_changes"] == 0


def test_discover_adaptive_band_large_cut(client, tmp_path):
    """
    Verify adaptive band handles cuts > 30 seconds (exceeding original 30s band)
    without truncation or failure.
    """
    # 45s video: 5s red + 35s yellow + 5s blue
    v1 = tmp_path / "v1.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "color=c=red:s=320x240:d=5.0:r=10",
        "-f", "lavfi", "-i", "color=c=yellow:s=320x240:d=35.0:r=10",
        "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=5.0:r=10",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=45.0",
        "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[outv]",
        "-map", "[outv]", "-map", "3:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(v1),
    ], check=True)

    # 10s video: 5s red + 5s blue (35s yellow segment removed!)
    v2 = tmp_path / "v2.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", "color=c=red:s=320x240:d=5.0:r=10",
        "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=5.0:r=10",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=10.0",
        "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[outv]",
        "-map", "[outv]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(v2),
    ], check=True)

    response = client.post(
        "/discover",
        files={
            "pre_final": ("v1.mp4", v1.read_bytes(), "video/mp4"),
            "final": ("v2.mp4", v2.read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["summary"]["timing"] >= 1
    assert data["summary"]["visual"] == 0
    timing_change = next(c for c in data["changes"] if c["kind"] == "TIMING")
    assert "segment_removed_with_aligned_flanks" in timing_change["evidence"]["reason_codes"]
    assert timing_change["confidence"] == "HIGH"


def test_discover_band_overflow_explicit_review(client, tmp_path, monkeypatch):
    """
    When timeline divergence exceeds the maximum supported alignment band (120s),
    an explicit REVIEW change must be returned instead of silent truncation.
    """
    v1 = _create_synthetic_video(tmp_path / "v1.mp4", duration=3.0, color="blue")
    v2 = _create_synthetic_video(tmp_path / "v2.mp4", duration=3.0, color="blue")

    # Simulate a huge duration difference (> 115s)
    monkeypatch.setattr(discovery, "duration_seconds", lambda p: 150.0 if "pre" in str(p).lower() else 5.0)

    response = client.post(
        "/discover",
        files={
            "pre_final": ("v1.mp4", v1.read_bytes(), "video/mp4"),
            "final": ("v2.mp4", v2.read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["summary"]["review"] >= 1
    review_change = next(c for c in data["changes"] if c["kind"] == "REVIEW")
    assert "timeline_divergence_exceeds_band" in review_change["evidence"]["reason_codes"]
    assert review_change["confidence"] == "LOW"


def test_discover_audio_mute(client, tmp_path):
    # V1: 5s video with continuous audio
    v1 = _create_synthetic_video(tmp_path / "v1.mp4", duration=5.0, color="gray")
    # V2: Identical video, but audio muted between 1.5s and 3.5s
    v2 = tmp_path / "v2.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-i", str(v1),
        "-af", "volume=enable='between(t,1.5,3.5)':volume=0",
        "-c:v", "copy", "-c:a", "aac", str(v2),
    ], check=True)

    response = client.post(
        "/discover",
        files={
            "pre_final": ("v1.mp4", v1.read_bytes(), "video/mp4"),
            "final": ("v2.mp4", v2.read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["summary"]["audio"] >= 1
    assert data["summary"]["visual"] == 0
    assert data["summary"]["timing"] == 0
    audio_change = next(c for c in data["changes"] if c["kind"] == "AUDIO")
    assert "local_audio_muted" in audio_change["evidence"]["reason_codes"]


def test_discover_encoding_noise(client, tmp_path):
    # V1 at crf=18
    v1 = _create_synthetic_video(tmp_path / "v1.mp4", duration=3.0, color="cyan", crf=18)
    # V2 re-encoded at crf=28 with lower audio bitrate
    v2 = tmp_path / "v2.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-i", str(v1),
        "-c:v", "libx264", "-crf", "28", "-c:a", "aac", "-b:a", "64k",
        str(v2),
    ], check=True)

    response = client.post(
        "/discover",
        files={
            "pre_final": ("v1.mp4", v1.read_bytes(), "video/mp4"),
            "final": ("v2.mp4", v2.read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    # Encoding noise should not produce false positive changes
    assert data["summary"]["total_changes"] == 0


def test_discover_api_endpoints_and_persistence(client, tmp_path):
    v1 = _create_synthetic_video(tmp_path / "v1.mp4", duration=3.0, color="magenta")
    response = client.post(
        "/discover",
        files={
            "pre_final": ("v1.mp4", v1.read_bytes(), "video/mp4"),
            "final": ("v2.mp4", v1.read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 200
    report = response.json()
    report_id = report["report_id"]

    # Verify report persistence
    get_res = client.get(f"/discover/{report_id}")
    assert get_res.status_code == 200
    assert get_res.json() == report

    # Verify export
    export_res = client.get(f"/discover/{report_id}/export")
    assert export_res.status_code == 200
    assert export_res.json() == report
    assert export_res.headers["content-type"] == "application/json"
    assert export_res.headers["content-disposition"] == f'attachment; filename="editdiff-discover-{report_id}.json"'

    # Verify disk persistence
    stored_path = main.DISCOVER_REPORTS / f"{report_id}.json"
    assert DiscoverResponse.model_validate_json(stored_path.read_text()).model_dump(mode="json") == report

    # Verify uploads directory cleaned up
    assert list(main.UPLOADS.iterdir()) == []


@pytest.mark.parametrize("files,status", [
    ({}, 422),
    ({"pre_final": ("a.mp4", b"corrupt", "video/mp4")}, 422),
    ({"pre_final": ("a.mp4", b"", "video/mp4"), "final": ("b.mp4", b"corrupt", "video/mp4")}, 400),
    ({"pre_final": ("a.mp4", b"corrupt", "video/mp4"), "final": ("b.mp4", b"corrupt", "video/mp4")}, 422),
])
def test_discover_invalid_uploads(client, files, status):
    response = client.post("/discover", files=files)
    assert response.status_code == status
    assert ":\\" not in response.text
    assert list(main.UPLOADS.iterdir()) == []


def test_discover_upload_limit(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 2)
    response = client.post(
        "/discover",
        files={"pre_final": ("a.mp4", b"123", "video/mp4"), "final": ("b.mp4", b"123", "video/mp4")},
    )
    assert response.status_code == 413
    assert list(main.UPLOADS.iterdir()) == []


@pytest.mark.parametrize("report_id", ["missing", "abcdef123456", "..", "ABCDEF123456"])
def test_discover_missing_reports(client, report_id):
    assert client.get(f"/discover/{report_id}").status_code == 404
    assert client.get(f"/discover/{report_id}/export").status_code == 404


def test_discover_canonical_demo_and_evidence_serving(client, sample):
    v1_bytes = (sample / "demo-v1.mp4").read_bytes()
    v2_bytes = (sample / "demo-v2.mp4").read_bytes()
    response = client.post(
        "/discover",
        files={
            "pre_final": ("demo-v1.mp4", v1_bytes, "video/mp4"),
            "final": ("demo-v2.mp4", v2_bytes, "video/mp4"),
        },
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["pre_final_duration_seconds"] == 14.0
    assert report["final_duration_seconds"] == 13.0
    assert report["duration_delta_seconds"] == -1.0
    assert report["summary"]["total_changes"] >= 1
    # Check that every change has valid evidence frame paths that serve images
    for change in report["changes"]:
        ev = change["evidence"]
        for frame_key in ("pre_final_frame_path", "final_frame_path"):
            path = ev[frame_key]
            if path:
                assert path.startswith(f"/evidence/{report['report_id']}/")
                img_res = client.get(path)
                assert img_res.status_code == 200
                assert img_res.headers["content-type"] == "image/jpeg"
