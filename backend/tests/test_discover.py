import subprocess
from pathlib import Path
import pytest
from app import discovery, main
from app.models import ChangeConfidence, ChangeKind, DiscoverResponse
from app.semantic import TextChangeFinding


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


def _create_pattern_video(path: Path, duration: float = 4.0, crf: int = 18) -> Path:
    subprocess.run([
        "ffmpeg", "-v", "error", "-y",
        "-f", "lavfi", "-i", f"testsrc2=s=320x240:d={duration}:r=10",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf),
        "-c:a", "aac", "-b:a", "128k", str(path),
    ], check=True)
    return path


def _filtered_copy(source: Path, target: Path, video_filter: str, crf: int = 18) -> Path:
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", str(source),
        "-vf", video_filter,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf),
        "-c:a", "copy", str(target),
    ], check=True)
    return target


def _drawtext_font_filter() -> str:
    candidates = (
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    )
    font_path = next(path for path in candidates if path.is_file())
    escaped = str(font_path).replace("\\", "/").replace(":", "\\:")
    return f"drawtext=fontfile='{escaped}':"


def _discover_pair(client, v1: Path, v2: Path) -> dict:
    response = client.post(
        "/discover",
        files={
            "pre_final": ("v1.mp4", v1.read_bytes(), "video/mp4"),
            "final": ("v2.mp4", v2.read_bytes(), "video/mp4"),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _assert_one_visual(data: dict) -> None:
    assert data["summary"]["visual"] == 1
    assert data["summary"]["timing"] == 0
    change = next(change for change in data["changes"] if change["kind"] == "VISUAL")
    assert change["description"] == "The aligned visual content differs materially between versions."
    metric_names = {metric["name"] for metric in change["evidence"]["metrics"]}
    assert {
        "global_mean_difference",
        "changed_pixel_ratio",
        "max_tile_difference",
        "p95_tile_difference",
        "color_difference",
        "edge_change_ratio",
        "orb_match_ratio",
        "supporting_frame_count",
    } <= metric_names
    assert "multi_frame_verification" in change["evidence"]["methods"]


def _single_visual_region() -> tuple[discovery.CandidateRegion, discovery.AlignmentStep]:
    step = discovery.AlignmentStep(
        kind="REPLACE",
        i=0,
        j=0,
        t1=1.25,
        t2=1.5,
        d_vis=0.01,
        a1=0.0,
        a2=0.0,
    )
    region = discovery.CandidateRegion(
        kind="VISUAL",
        t1_start=1.25,
        t1_end=1.25,
        t2_start=1.5,
        t2_end=1.5,
        start_step_idx=0,
        end_step_idx=0,
        steps=[step],
    )
    return region, step


def _visual_metrics(*, moderate: bool, very_strong: bool) -> discovery.VisualMetrics:
    return discovery.VisualMetrics(
        global_mean_difference=0.01,
        changed_pixel_ratio=0.01,
        max_tile_difference=0.01,
        p95_tile_difference=0.01,
        changed_tile_ratio=0.01,
        color_difference=0.01,
        edge_change_ratio=0.01,
        orb_match_ratio=0.9,
        moderate=moderate,
        very_strong=very_strong,
    )


def _text_finding(
    *,
    before: str | None,
    after: str | None,
    is_text_change: bool = True,
    confidence: str = "HIGH",
    supporting: list[int] | None = None,
) -> TextChangeFinding:
    return TextChangeFinding(
        has_visible_text=before is not None or after is not None,
        is_text_change=is_text_change,
        before_text=before,
        after_text=after,
        confidence=confidence,
        supporting_frame_indices=[0] if supporting is None else supporting,
        explanation="Only the readable visible wording differs." if is_text_change else "Readable wording is unchanged.",
    )


def _classify_mocked_visuals(tmp_path, monkeypatch, findings):
    regions_and_steps = [_single_visual_region() for _ in findings]
    regions = [item[0] for item in regions_and_steps]
    steps = [item[1] for item in regions_and_steps]
    finding_iter = iter(findings)
    monkeypatch.setattr(discovery, "visual_metrics_at", lambda *args: _visual_metrics(moderate=True, very_strong=True))
    monkeypatch.setattr(discovery, "extract_frame", lambda path, timestamp, out_path: out_path)
    monkeypatch.setattr(discovery, "text_semantic_configured", lambda: True)
    monkeypatch.setattr(discovery, "verify_text_change", lambda frames: (next(finding_iter), "available"))
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    return discovery.classify_and_verify_changes(
        regions,
        steps,
        step=0.25,
        v1_path=tmp_path / "v1.mp4",
        v2_path=tmp_path / "v2.mp4",
        evidence_dir=evidence_dir,
        d1=3.0,
        d2=3.0,
    )


def test_very_strong_frame_is_supporting_evidence(tmp_path, monkeypatch):
    region, step = _single_visual_region()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    monkeypatch.setattr(
        discovery,
        "visual_metrics_at",
        lambda *args: _visual_metrics(moderate=False, very_strong=True),
    )
    monkeypatch.setattr(discovery, "extract_frame", lambda path, timestamp, out_path: out_path)

    changes = discovery.classify_and_verify_changes(
        [region],
        [step],
        step=0.25,
        v1_path=tmp_path / "v1.mp4",
        v2_path=tmp_path / "v2.mp4",
        evidence_dir=evidence_dir,
        d1=3.0,
        d2=3.0,
    )

    assert len(changes) == 1
    assert changes[0].kind == ChangeKind.VISUAL
    assert changes[0].confidence == ChangeConfidence.MEDIUM
    assert changes[0].evidence.pre_final_timestamp_seconds == 1.25
    assert changes[0].evidence.final_timestamp_seconds == 1.5
    assert changes[0].evidence.pre_final_frame_path.endswith("change-001-pre.jpg")
    assert changes[0].evidence.final_frame_path.endswith("change-001-final.jpg")


def test_non_supporting_frame_does_not_emit_visual(tmp_path, monkeypatch):
    region, step = _single_visual_region()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    monkeypatch.setattr(
        discovery,
        "visual_metrics_at",
        lambda *args: _visual_metrics(moderate=False, very_strong=False),
    )
    monkeypatch.setattr(discovery, "extract_frame", lambda path, timestamp, out_path: out_path)

    changes = discovery.classify_and_verify_changes(
        [region],
        [step],
        step=0.25,
        v1_path=tmp_path / "v1.mp4",
        v2_path=tmp_path / "v2.mp4",
        evidence_dir=evidence_dir,
        d1=3.0,
        d2=3.0,
    )

    assert changes == []


@pytest.mark.parametrize(("before", "after", "reason"), [
    ("DRAFT CUT", "FINAL CUT", "visible_text_replaced"),
    (None, "LIMITED OFFER", "visible_text_added"),
    ("WATERMARK", None, "visible_text_removed"),
])
def test_confirmed_visual_converts_to_text(tmp_path, monkeypatch, before, after, reason):
    changes = _classify_mocked_visuals(
        tmp_path,
        monkeypatch,
        [_text_finding(before=before, after=after)],
    )

    assert len(changes) == 1
    change = changes[0]
    assert change.kind == ChangeKind.TEXT
    assert change.title == "TEXT CHANGE"
    assert change.confidence == ChangeConfidence.MEDIUM
    visible_text = next(metric for metric in change.evidence.metrics if metric.name == "visible_text")
    assert visible_text.v1 == before
    assert visible_text.v2 == after
    assert "gemini_visible_text_comparison" in change.evidence.methods
    assert "visible_text_content_changed" in change.evidence.reason_codes
    assert reason in change.evidence.reason_codes
    assert change.evidence.text_semantic_status == "classified_text"
    assert change.evidence.text_before == before
    assert change.evidence.text_after == after
    assert change.evidence.pre_final_timestamp_seconds == 1.25
    assert change.evidence.final_timestamp_seconds == 1.5


@pytest.mark.parametrize(("finding", "expected_status"), [
    (_text_finding(before="FINAL CUT", after="FINAL CUT", is_text_change=False), "same_text"),
    (_text_finding(before=None, after=None, is_text_change=False, confidence="HIGH", supporting=[]), "unreadable"),
])
def test_same_or_unreadable_text_stays_visual(tmp_path, monkeypatch, finding, expected_status):
    changes = _classify_mocked_visuals(tmp_path, monkeypatch, [finding])
    assert len(changes) == 1
    assert changes[0].kind == ChangeKind.VISUAL
    assert changes[0].evidence.text_semantic_status == expected_status


def test_text_semantic_unavailable_stays_visual(tmp_path, monkeypatch):
    region, step = _single_visual_region()
    monkeypatch.setattr(discovery, "visual_metrics_at", lambda *args: _visual_metrics(moderate=True, very_strong=True))
    monkeypatch.setattr(discovery, "extract_frame", lambda path, timestamp, out_path: out_path)
    monkeypatch.setattr(discovery, "text_semantic_configured", lambda: False)
    monkeypatch.setattr(
        discovery,
        "verify_text_change",
        lambda frames: pytest.fail("Semantic classifier must not run without configuration"),
    )
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()

    changes = discovery.classify_and_verify_changes(
        [region], [step], 0.25, tmp_path / "v1.mp4", tmp_path / "v2.mp4", evidence_dir, 3.0, 3.0
    )
    assert len(changes) == 1
    assert changes[0].kind == ChangeKind.VISUAL
    assert changes[0].evidence.text_semantic_status == "not_configured"


def test_malformed_text_semantic_response_stays_visual(tmp_path, monkeypatch, caplog):
    region, step = _single_visual_region()
    monkeypatch.setattr(discovery, "visual_metrics_at", lambda *args: _visual_metrics(moderate=True, very_strong=True))
    monkeypatch.setattr(discovery, "extract_frame", lambda path, timestamp, out_path: out_path)
    monkeypatch.setattr(discovery, "text_semantic_configured", lambda: True)
    secret_detail = "bad JSON containing test-secret-key"
    monkeypatch.setattr(
        discovery,
        "verify_text_change",
        lambda frames: (_ for _ in ()).throw(ValueError(secret_detail)),
    )
    caplog.set_level("INFO", logger=discovery.__name__)
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()

    changes = discovery.classify_and_verify_changes(
        [region], [step], 0.25, tmp_path / "v1.mp4", tmp_path / "v2.mp4", evidence_dir, 3.0, 3.0
    )
    assert len(changes) == 1
    assert changes[0].kind == ChangeKind.VISUAL
    assert changes[0].evidence.text_semantic_status == "invalid_response"
    assert "TEXT_CLASSIFICATION report=evidence change=change-001 status=invalid_response" in caplog.text
    assert secret_detail not in caplog.text


def test_text_semantic_timeout_stays_visual(tmp_path, monkeypatch):
    region, step = _single_visual_region()
    monkeypatch.setattr(discovery, "visual_metrics_at", lambda *args: _visual_metrics(moderate=True, very_strong=True))
    monkeypatch.setattr(discovery, "extract_frame", lambda path, timestamp, out_path: out_path)
    monkeypatch.setattr(discovery, "text_semantic_configured", lambda: True)
    monkeypatch.setattr(discovery, "verify_text_change", lambda frames: (None, "timeout"))
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()

    changes = discovery.classify_and_verify_changes(
        [region], [step], 0.25, tmp_path / "v1.mp4", tmp_path / "v2.mp4", evidence_dir, 3.0, 3.0
    )
    assert changes[0].kind == ChangeKind.VISUAL
    assert changes[0].evidence.text_semantic_status == "timeout"


def test_low_confidence_text_stays_visual(tmp_path, monkeypatch):
    finding = _text_finding(before="DRAFT CUT", after="FINAL CUT", confidence="LOW")
    change = _classify_mocked_visuals(tmp_path, monkeypatch, [finding])[0]
    assert change.kind == ChangeKind.VISUAL
    assert change.evidence.text_semantic_status == "low_confidence"
    assert change.evidence.text_before == "DRAFT CUT"
    assert change.evidence.text_after == "FINAL CUT"


def test_only_textual_visual_edit_converts(tmp_path, monkeypatch):
    findings = [
        _text_finding(before="DRAFT CUT", after="FINAL CUT"),
        _text_finding(before="FINAL CUT", after="FINAL CUT", is_text_change=False),
        _text_finding(before=None, after=None, is_text_change=False, confidence="LOW", supporting=[]),
    ]
    changes = _classify_mocked_visuals(tmp_path, monkeypatch, findings)
    assert [change.kind for change in changes] == [ChangeKind.TEXT, ChangeKind.VISUAL, ChangeKind.VISUAL]


def test_text_classification_call_bound(tmp_path, monkeypatch):
    regions_and_steps = [_single_visual_region() for _ in range(10)]
    calls = 0

    def unavailable(frames):
        nonlocal calls
        calls += 1
        return None, "api_error"

    monkeypatch.setattr(discovery, "visual_metrics_at", lambda *args: _visual_metrics(moderate=True, very_strong=True))
    monkeypatch.setattr(discovery, "extract_frame", lambda path, timestamp, out_path: out_path)
    monkeypatch.setattr(discovery, "text_semantic_configured", lambda: True)
    monkeypatch.setattr(discovery, "verify_text_change", unavailable)
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    changes = discovery.classify_and_verify_changes(
        [item[0] for item in regions_and_steps],
        [item[1] for item in regions_and_steps],
        0.25,
        tmp_path / "v1.mp4",
        tmp_path / "v2.mp4",
        evidence_dir,
        3.0,
        3.0,
    )

    assert len(changes) == 10
    assert calls == discovery.MAX_TEXT_CLASSIFICATIONS_PER_REPORT == 8
    assert [change.evidence.text_semantic_status for change in changes[-2:]] == [
        "call_limit_reached",
        "call_limit_reached",
    ]


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


def test_discover_small_title_change(client, tmp_path):
    source = _create_pattern_video(tmp_path / "source.mp4")
    common = ":x=(w-text_w)/2:y=28:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.75"
    font = _drawtext_font_filter()
    v1 = _filtered_copy(source, tmp_path / "v1.mp4", font + "text='EXPORT V1'" + common)
    v2 = _filtered_copy(source, tmp_path / "v2.mp4", font + "text='FINAL CUT'" + common)
    _assert_one_visual(_discover_pair(client, v1, v2))


def test_discover_text_conversion_updates_summary(client, tmp_path, monkeypatch):
    source = _create_pattern_video(tmp_path / "source.mp4")
    common = ":x=(w-text_w)/2:y=28:fontsize=24:fontcolor=white:box=1:boxcolor=black@0.75"
    font = _drawtext_font_filter()
    v1 = _filtered_copy(source, tmp_path / "v1.mp4", font + "text='DRAFT CUT'" + common)
    v2 = _filtered_copy(source, tmp_path / "v2.mp4", font + "text='FINAL CUT'" + common)
    calls = []

    def classify(frames):
        calls.append(frames)
        return _text_finding(before="DRAFT CUT", after="FINAL CUT"), "available"

    monkeypatch.setattr(discovery, "text_semantic_configured", lambda: True)
    monkeypatch.setattr(discovery, "verify_text_change", classify)
    data = _discover_pair(client, v1, v2)

    assert len(calls) == 1
    assert len(calls[0]) <= 3
    assert data["summary"] == {
        "total_changes": 1,
        "visual": 0,
        "timing": 0,
        "audio": 0,
        "text": 1,
        "review": 0,
    }
    change = data["changes"][0]
    assert change["kind"] == "TEXT"
    assert change["evidence"]["text_semantic_status"] == "classified_text"
    assert change["evidence"]["text_before"] == "DRAFT CUT"
    assert change["evidence"]["text_after"] == "FINAL CUT"
    visible_text = next(metric for metric in change["evidence"]["metrics"] if metric["name"] == "visible_text")
    assert visible_text["v1"] == "DRAFT CUT"
    assert visible_text["v2"] == "FINAL CUT"


def test_discover_same_text_style_change_stays_visual(client, tmp_path, monkeypatch):
    source = _create_pattern_video(tmp_path / "source.mp4")
    font = _drawtext_font_filter()
    v1 = _filtered_copy(
        source,
        tmp_path / "v1.mp4",
        font + "text='FINAL CUT':x=(w-text_w)/2:y=28:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.75",
    )
    v2 = _filtered_copy(
        source,
        tmp_path / "v2.mp4",
        font + "text='FINAL CUT':x=(w-text_w)/2:y=28:fontsize=32:fontcolor=yellow:box=1:boxcolor=black@0.75",
    )
    monkeypatch.setattr(discovery, "text_semantic_configured", lambda: True)
    monkeypatch.setattr(
        discovery,
        "verify_text_change",
        lambda frames: (
            _text_finding(before="FINAL CUT", after="FINAL CUT", is_text_change=False),
            "available",
        ),
    )
    data = _discover_pair(client, v1, v2)

    assert data["summary"]["total_changes"] == 1
    assert data["summary"]["visual"] == 1
    assert data["summary"]["text"] == 0
    assert data["changes"][0]["kind"] == "VISUAL"
    assert data["changes"][0]["evidence"]["text_semantic_status"] == "same_text"


def test_discover_small_logo_added(client, tmp_path):
    v1 = _create_pattern_video(tmp_path / "v1.mp4")
    v2 = _filtered_copy(v1, tmp_path / "v2.mp4", "drawbox=x=255:y=15:w=48:h=40:color=yellow:t=fill")
    _assert_one_visual(_discover_pair(client, v1, v2))


def test_discover_small_logo_removed(client, tmp_path):
    source = _create_pattern_video(tmp_path / "source.mp4")
    with_logo = _filtered_copy(source, tmp_path / "with-logo.mp4", "drawbox=x=255:y=15:w=48:h=40:color=yellow:t=fill")
    _assert_one_visual(_discover_pair(client, with_logo, source))


def test_discover_lower_third_changed(client, tmp_path):
    source = _create_pattern_video(tmp_path / "source.mp4")
    v1 = _filtered_copy(source, tmp_path / "v1.mp4", "drawbox=x=18:y=185:w=190:h=34:color=blue@0.9:t=fill")
    v2 = _filtered_copy(source, tmp_path / "v2.mp4", "drawbox=x=18:y=185:w=190:h=34:color=orange@0.9:t=fill")
    _assert_one_visual(_discover_pair(client, v1, v2))


def test_discover_four_percent_crop_zoom(client, tmp_path):
    v1 = _create_pattern_video(tmp_path / "v1.mp4")
    v2 = _filtered_copy(v1, tmp_path / "v2.mp4", "crop=iw*0.96:ih*0.96,scale=320:240")
    _assert_one_visual(_discover_pair(client, v1, v2))


def test_discover_color_grade_change(client, tmp_path):
    v1 = _create_pattern_video(tmp_path / "v1.mp4")
    v2 = _filtered_copy(v1, tmp_path / "v2.mp4", "hue=h=45")
    _assert_one_visual(_discover_pair(client, v1, v2))


def test_discover_short_visual_replacement(client, tmp_path):
    v1 = _create_pattern_video(tmp_path / "v1.mp4")
    v2 = _filtered_copy(
        v1,
        tmp_path / "v2.mp4",
        "drawbox=x=0:y=0:w=iw:h=ih:color=purple:t=fill:enable='between(t,2.0,2.4)'",
    )
    _assert_one_visual(_discover_pair(client, v1, v2))


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


def test_discover_crf_18_to_30_is_not_visual(client, tmp_path):
    v1 = _create_pattern_video(tmp_path / "v1.mp4", crf=18)
    v2 = _filtered_copy(v1, tmp_path / "v2.mp4", "null", crf=30)
    data = _discover_pair(client, v1, v2)
    assert data["summary"]["visual"] == 0
    assert data["summary"]["total_changes"] == 0


def test_discover_bitrate_change_is_not_visual(client, tmp_path):
    v1 = _create_pattern_video(tmp_path / "v1.mp4", crf=18)
    v2 = tmp_path / "v2.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-i", str(v1),
        "-c:v", "libx264", "-b:v", "180k", "-maxrate", "180k", "-bufsize", "360k",
        "-c:a", "copy", str(v2),
    ], check=True)
    data = _discover_pair(client, v1, v2)
    assert data["summary"]["visual"] == 0
    assert data["summary"]["total_changes"] == 0


def test_discover_scale_round_trip_noise_is_not_visual(client, tmp_path):
    v1 = _create_pattern_video(tmp_path / "v1.mp4", crf=18)
    v2 = _filtered_copy(v1, tmp_path / "v2.mp4", "scale=352:264,scale=320:240", crf=24)
    data = _discover_pair(client, v1, v2)
    assert data["summary"]["visual"] == 0
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
