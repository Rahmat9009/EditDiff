import json
from pathlib import Path

import pytest

from app import main, technical as technical_module
from app.models import (
    ChangeConfidence,
    ChangeDisposition,
    ChangeEvidence,
    ChangeKind,
    CheckKind,
    DetectedChange,
    Evidence,
    ReleaseChangeAssessment,
    ReleaseDecision,
    ReleaseGateResult,
    RevisionRequest,
    TechnicalCheck,
    TechnicalCheckSeverity,
    TechnicalCheckStatus,
    Verdict,
    VerificationResult,
)
from app.release_gate import build_summary, correlate_changes, decide_release
from app.technical import (
    _audio_dropout_check,
    _audio_track_check,
    _black_frame_check,
    _duration_check,
    _resolution_check,
)


def revision(
    request_id: str = "revision-001",
    kind: CheckKind = CheckKind.MUTE_AUDIO,
    verdict: Verdict = Verdict.PASS,
    start: float = 1.0,
    end: float = 2.0,
    old_text: str | None = None,
    new_text: str | None = None,
) -> VerificationResult:
    return VerificationResult(
        request=RevisionRequest(
            id=request_id, raw_text="requested edit", kind=kind, timestamp_seconds=(start + end) / 2,
            expected_old_text=old_text, expected_new_text=new_text,
        ),
        verdict=verdict,
        confidence=0.9,
        evidence=Evidence(
            explanation="verification", window_start_seconds=start, window_end_seconds=end,
            methods=["test"], reason_codes=["test"],
        ),
    )


def change(
    change_id: str = "change-001",
    kind: ChangeKind = ChangeKind.AUDIO,
    start: float | None = 1.25,
    end: float | None = 1.75,
    text_before: str | None = None,
    text_after: str | None = None,
) -> DetectedChange:
    return DetectedChange(
        id=change_id, kind=kind, confidence=ChangeConfidence.HIGH,
        title="CHANGE", description="change",
        evidence=ChangeEvidence(
            window_start_pre_final=start, window_end_pre_final=end,
            pre_final_timestamp_seconds=start, final_timestamp_seconds=start,
            text_before=text_before, text_after=text_after, explanation="change",
        ),
    )


def technical(
    status: TechnicalCheckStatus = TechnicalCheckStatus.PASS,
    severity: TechnicalCheckSeverity = TechnicalCheckSeverity.BLOCKING,
) -> TechnicalCheck:
    return TechnicalCheck(
        id="technical", label="Technical", status=status, severity=severity,
        confidence=0.99, explanation="technical", evidence=Evidence(explanation="technical"),
    )


@pytest.mark.parametrize(
    ("verdict", "disposition", "technical_status", "expected"),
    [
        (Verdict.PASS, ChangeDisposition.ACCOUNTED_FOR, TechnicalCheckStatus.PASS,
         ReleaseDecision.READY_TO_PUBLISH),
        (Verdict.REVIEW, ChangeDisposition.ACCOUNTED_FOR, TechnicalCheckStatus.PASS,
         ReleaseDecision.NEEDS_REVIEW),
        (Verdict.PASS, ChangeDisposition.UNEXPECTED, TechnicalCheckStatus.PASS,
         ReleaseDecision.NEEDS_REVIEW),
        (Verdict.PASS, ChangeDisposition.REVIEW, TechnicalCheckStatus.PASS,
         ReleaseDecision.NEEDS_REVIEW),
        (Verdict.PASS, ChangeDisposition.ACCOUNTED_FOR, TechnicalCheckStatus.REVIEW,
         ReleaseDecision.NEEDS_REVIEW),
        (Verdict.FAIL, ChangeDisposition.UNEXPECTED, TechnicalCheckStatus.PASS,
         ReleaseDecision.BLOCKED),
        (Verdict.PASS, ChangeDisposition.ACCOUNTED_FOR, TechnicalCheckStatus.FAIL,
         ReleaseDecision.BLOCKED),
    ],
)
def test_decision_matrix(verdict, disposition, technical_status, expected):
    requested = [revision(verdict=verdict)]
    discovered = [ReleaseChangeAssessment(
        change=change(), disposition=disposition, matched_revision_ids=["revision-001"], explanation="test"
    )]
    decision, reasons = decide_release(requested, discovered, [technical(technical_status)])
    assert decision == expected
    assert reasons


def test_exact_requested_change_correlation():
    assessment = correlate_changes([change()], [revision()])[0]
    assert assessment.disposition == ChangeDisposition.ACCOUNTED_FOR
    assert assessment.matched_revision_ids == ["revision-001"]


def test_nearby_is_not_overlap():
    assessment = correlate_changes([change(start=2.01, end=2.4)], [revision(end=2.0)])[0]
    assert assessment.disposition == ChangeDisposition.UNEXPECTED


def test_ambiguous_correlation_is_review():
    revisions = [revision("revision-001"), revision("revision-002", start=1.4, end=2.4)]
    assessment = correlate_changes([change()], revisions)[0]
    assert assessment.disposition == ChangeDisposition.REVIEW
    assert assessment.matched_revision_ids == ["revision-001", "revision-002"]


def test_many_changes_to_one_revision_is_review():
    assessments = correlate_changes([
        change("change-001", start=1.1, end=1.4),
        change("change-002", start=1.6, end=1.9),
    ], [revision()])
    assert [item.disposition for item in assessments] == [
        ChangeDisposition.REVIEW, ChangeDisposition.REVIEW,
    ]


@pytest.mark.parametrize("verdict", [Verdict.FAIL, Verdict.REVIEW])
def test_only_pass_may_account_for_change(verdict):
    assessment = correlate_changes([change()], [revision(verdict=verdict)])[0]
    assert assessment.disposition == ChangeDisposition.REVIEW


def test_requested_mute_is_not_reported_as_regression():
    assessment = correlate_changes([change(kind=ChangeKind.AUDIO)], [revision(kind=CheckKind.MUTE_AUDIO)])[0]
    assert assessment.disposition == ChangeDisposition.ACCOUNTED_FOR


def test_requested_timing_cut_is_not_reported_as_regression():
    assessment = correlate_changes(
        [change(kind=ChangeKind.TIMING)], [revision(kind=CheckKind.REMOVE_PAUSE)]
    )[0]
    assert assessment.disposition == ChangeDisposition.ACCOUNTED_FOR


def test_passed_revision_plus_unrelated_logo_disappearance_needs_review():
    assessments = correlate_changes([
        change("change-001", ChangeKind.AUDIO),
        change("change-002", ChangeKind.VISUAL, 5.0, 6.0),
    ], [revision()])
    assert [item.disposition for item in assessments] == [
        ChangeDisposition.ACCOUNTED_FOR, ChangeDisposition.UNEXPECTED,
    ]
    decision, _ = decide_release([revision()], assessments, [technical()])
    assert decision == ReleaseDecision.NEEDS_REVIEW


def test_revision_fail_blocks():
    decision, _ = decide_release([revision(verdict=Verdict.FAIL)], [], [technical()])
    assert decision == ReleaseDecision.BLOCKED


def test_unexpected_change_alone_does_not_block():
    assessment = ReleaseChangeAssessment(
        change=change(), disposition=ChangeDisposition.UNEXPECTED, explanation="unexpected"
    )
    decision, _ = decide_release([revision()], [assessment], [technical()])
    assert decision == ReleaseDecision.NEEDS_REVIEW


def test_strong_blocking_technical_failure_blocks():
    decision, _ = decide_release([revision()], [], [technical(TechnicalCheckStatus.FAIL)])
    assert decision == ReleaseDecision.BLOCKED


def test_advisory_failure_does_not_block():
    decision, _ = decide_release(
        [revision()], [], [technical(TechnicalCheckStatus.FAIL, TechnicalCheckSeverity.ADVISORY)]
    )
    assert decision == ReleaseDecision.NEEDS_REVIEW


def test_resolution_and_duration_mismatch_are_review():
    pre_probe = {"streams": [{"codec_type": "video", "width": 1920, "height": 1080}]}
    final_probe = {"streams": [{"codec_type": "video", "width": 1080, "height": 1080}]}
    assert _resolution_check(pre_probe, final_probe).status == TechnicalCheckStatus.REVIEW
    assert _duration_check(10.0, 12.0).status == TechnicalCheckStatus.REVIEW


def test_complete_audio_track_loss_is_strong_blocking_failure():
    pre_probe = {"streams": [{"codec_type": "video"}, {"codec_type": "audio"}]}
    final_probe = {"streams": [{"codec_type": "video"}]}
    result = _audio_track_check(pre_probe, final_probe)
    assert result.status == TechnicalCheckStatus.FAIL
    assert result.severity == TechnicalCheckSeverity.BLOCKING
    assert result.confidence == 1.0


def test_sustained_aligned_audio_dropout_blocks_unless_accounted_for():
    probe = {"streams": [{"codec_type": "video"}, {"codec_type": "audio"}]}
    dropout = change(kind=ChangeKind.AUDIO, start=1.0, end=4.5)
    dropout.evidence.window_start_final = 1.0
    dropout.evidence.window_end_final = 4.5
    dropout.evidence.reason_codes = ["local_audio_muted"]
    from app.models import DiscoverResponse, DiscoverSummary
    discovery = DiscoverResponse(
        report_id="abcdef123456", pre_final_duration_seconds=6,
        final_duration_seconds=6, duration_delta_seconds=0,
        summary=DiscoverSummary(total_changes=1, visual=0, timing=0, audio=1, text=0, review=0),
        changes=[dropout],
    )
    assert _audio_dropout_check(probe, probe, discovery, set()).status == TechnicalCheckStatus.FAIL
    assert _audio_dropout_check(probe, probe, discovery, {dropout.id}).status == TechnicalCheckStatus.PASS


def test_sustained_black_regression_is_blocking(tmp_path, monkeypatch):
    flags = iter([[False] * 8, [True] * 4 + [False] * 4])
    monkeypatch.setattr(technical_module, "_black_flags", lambda *args: next(flags))
    result = _black_frame_check(tmp_path / "pre.mp4", tmp_path / "final.mp4", 2.0, 2.0)
    assert result.status == TechnicalCheckStatus.FAIL
    assert result.severity == TechnicalCheckSeverity.BLOCKING


def test_gemini_unavailable_cannot_fabricate_text_correlation():
    # Without semantic text classification, Discover conservatively emits VISUAL.
    assessment = correlate_changes(
        [change(kind=ChangeKind.VISUAL)],
        [revision(kind=CheckKind.TEXT_CHANGE, old_text="DRAFT", new_text="FINAL")],
    )[0]
    assert assessment.disposition == ChangeDisposition.UNEXPECTED


def test_exact_semantic_text_must_match_quoted_request():
    request = revision(
        kind=CheckKind.TEXT_CHANGE, old_text="DRAFT CUT", new_text="FINAL CUT"
    )
    matching = change(
        kind=ChangeKind.TEXT, text_before="DRAFT CUT", text_after="FINAL CUT"
    )
    mismatch = change(
        kind=ChangeKind.TEXT, text_before="DRAFT CUT", text_after="SOMETHING ELSE"
    )
    assert correlate_changes([matching], [request])[0].disposition == ChangeDisposition.ACCOUNTED_FOR
    assert correlate_changes([mismatch], [request])[0].disposition == ChangeDisposition.REVIEW


def _release_result(report_id: str) -> ReleaseGateResult:
    requested = [revision()]
    checks = [technical()]
    return ReleaseGateResult(
        report_id=report_id, decision=ReleaseDecision.READY_TO_PUBLISH,
        decision_reasons=["ready"], summary=build_summary(requested, [], checks),
        baseline_duration_seconds=4.0, candidate_duration_seconds=4.0,
        requested_revisions=requested, change_assessments=[], technical_checks=checks,
    )


def test_release_gate_upload_cleanup_persistence_retrieval_and_export(client, monkeypatch):
    def fake_saved(requests, pre_final_path, final_path, evidence_dir):
        assert pre_final_path.read_bytes() == b"pre"
        assert final_path.read_bytes() == b"final"
        result = _release_result(evidence_dir.name)
        target = main.RELEASE_GATE_REPORTS / f"{result.report_id}.json"
        target.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result

    monkeypatch.setattr(main, "_release_gate_saved", fake_saved)
    response = client.post(
        "/release-gate",
        files={
            "pre_final": ("pre.mp4", b"pre", "video/mp4"),
            "final": ("final.mp4", b"final", "video/mp4"),
        },
        data={"notes": "00:01.5 mute the background audio"},
    )
    assert response.status_code == 200, response.text
    report = response.json()
    report_id = report["report_id"]
    assert list(main.UPLOADS.iterdir()) == []
    assert client.get(f"/release-gate/{report_id}").json() == report
    exported = client.get(f"/release-gate/{report_id}/export")
    assert exported.json() == report
    assert exported.headers["content-disposition"] == (
        f'attachment; filename="editdiff-release-gate-{report_id}.json"'
    )


@pytest.mark.parametrize("report_id", ["missing", "abcdef123456", "..", "ABCDEF123456"])
def test_missing_release_gate_reports(client, report_id):
    assert client.get(f"/release-gate/{report_id}").status_code == 404
    assert client.get(f"/release-gate/{report_id}/export").status_code == 404


def test_release_gate_failed_upload_cleans_all_temporary_data(client):
    response = client.post(
        "/release-gate",
        files={
            "pre_final": ("pre.mp4", b"", "video/mp4"),
            "final": ("final.mp4", b"bad", "video/mp4"),
        },
        data={"notes": "00:01 mute audio"},
    )
    assert response.status_code == 400
    assert list(main.UPLOADS.iterdir()) == []
    assert list(main.EVIDENCE.iterdir()) == []
    assert list(main.RELEASE_GATE_REPORTS.iterdir()) == []


def test_release_gate_golden_fixture(client, sample):
    spec = json.loads((sample / "release-gate-golden.json").read_text(encoding="utf-8"))
    response = client.post(
        "/release-gate",
        files={
            "pre_final": (
                "pre-final.mp4", (sample / "release-gate-pre-final.mp4").read_bytes(), "video/mp4"
            ),
            "final": ("final.mp4", (sample / "release-gate-final.mp4").read_bytes(), "video/mp4"),
        },
        data={"notes": (sample / "release-gate-notes.txt").read_text(encoding="utf-8")},
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["decision"] == spec["expected_decision"]
    assert [item["verdict"] for item in report["requested_revisions"]] == spec["expected_requested_verdicts"]
    dispositions = [item["disposition"] for item in report["change_assessments"]]
    assert all(required in dispositions for required in spec["required_change_dispositions"])
    unexpected = [
        item for item in report["change_assessments"] if item["disposition"] == "UNEXPECTED"
    ]
    assert any(item["change"]["kind"] == spec["unexpected_change_kind"] for item in unexpected)
    assert report["summary"]["requested_passed"] == 1
    assert report["summary"]["unexpected_changes"] >= 1
    assert report["summary"]["technical_failed"] == 0
