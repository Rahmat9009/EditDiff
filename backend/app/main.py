from __future__ import annotations

import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from .discovery import discover_changes
from .media import MediaError, probe_media
from .models import AnalyzeResponse, DiscoverResponse, ReleaseGateResult, RevisionRequest
from .notes import parse_notes
from .release_gate import run_release_gate
from .semantic import text_semantic_readiness
from .verifier import verify

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / ".data"
UPLOADS = DATA / "uploads"
EVIDENCE = DATA / "evidence"
REPORTS = DATA / "reports"
DISCOVER_REPORTS = DATA / "discover_reports"
RELEASE_GATE_REPORTS = DATA / "release_gate_reports"
for directory in (UPLOADS, EVIDENCE, REPORTS, DISCOVER_REPORTS, RELEASE_GATE_REPORTS):
    directory.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = 250 * 1024 * 1024

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://frontend-two-self-17.vercel.app",
]
VERCEL_PREVIEW_ORIGIN_REGEX = (
    r"^https://frontend-[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
    r"-rahmat9009s-projects\.vercel\.app$"
)


def get_cors_origins(raw: str | None = None) -> list[str]:
    if raw is None:
        raw = os.getenv("CORS_ORIGINS")
    if raw is None:
        return list(DEFAULT_CORS_ORIGINS)
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins if origins else list(DEFAULT_CORS_ORIGINS)


app = FastAPI(title="EditDiff API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_origin_regex=VERCEL_PREVIEW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/evidence", StaticFiles(directory=EVIDENCE), name="evidence")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/semantic")
def health_semantic() -> dict[str, bool]:
    return text_semantic_readiness()


async def _save(upload: UploadFile, destination: Path) -> None:
    if not upload.filename:
        raise HTTPException(400, "Missing filename")
    size = 0
    with destination.open("wb") as output:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "Upload exceeds 250 MiB limit.")
            output.write(chunk)
    if size == 0:
        raise HTTPException(400, "Empty upload")


def _analyze_saved(requests: list[RevisionRequest], v1_path: Path, v2_path: Path, evidence_dir: Path) -> AnalyzeResponse:
    probe_media(v1_path)
    probe_media(v2_path)
    results = [verify(req, v1_path, v2_path, evidence_dir) for req in requests]
    summary = {"PASS": 0, "FAIL": 0, "REVIEW": 0}
    for result in results:
        summary[result.verdict.value] += 1
    report = AnalyzeResponse(report_id=evidence_dir.name, summary=summary, results=results)
    temporary = REPORTS / f"{report.report_id}.tmp"
    temporary.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(REPORTS / f"{report.report_id}.json")
    return report


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(v1: UploadFile = File(...), v2: UploadFile = File(...), notes: str = Form(...)) -> AnalyzeResponse:
    if len(notes) > 20000:
        raise HTTPException(400, "Notes exceed 20,000 characters.")
    requests = parse_notes(notes)
    if not requests or len(requests) > 30:
        raise HTTPException(400, "Provide between 1 and 30 revision notes.")
    report_id = uuid.uuid4().hex[:12]
    report_dir, evidence_dir = UPLOADS / report_id, EVIDENCE / report_id
    report_dir.mkdir(parents=True, exist_ok=False)
    evidence_dir.mkdir(parents=True, exist_ok=False)
    completed = False
    try:
        # Fixed names; client-supplied paths/extensions never become filesystem paths.
        v1_path, v2_path = report_dir / "v1.media", report_dir / "v2.media"
        await _save(v1, v1_path)
        await _save(v2, v2_path)
        report = await run_in_threadpool(_analyze_saved, requests, v1_path, v2_path, evidence_dir)
        completed = True
        return report
    except (MediaError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(422, "Could not decode uploaded videos within supported media limits.") from exc
    except FileNotFoundError as exc:
        raise HTTPException(503, "Required media processing service is unavailable.") from exc
    finally:
        await v1.close()
        await v2.close()
        shutil.rmtree(report_dir)
        if not completed:
            shutil.rmtree(evidence_dir)


def _load_report(report_id: str) -> AnalyzeResponse:
    if not re.fullmatch(r"[0-9a-f]{12}", report_id):
        raise HTTPException(404, "Report not found")
    path = REPORTS / f"{report_id}.json"
    if not path.is_file():
        raise HTTPException(404, "Report not found")
    return AnalyzeResponse.model_validate_json(path.read_text(encoding="utf-8"))


@app.get("/reports/{report_id}", response_model=AnalyzeResponse)
def get_report(report_id: str) -> AnalyzeResponse:
    return _load_report(report_id)


@app.get("/reports/{report_id}/export")
def export_report(report_id: str) -> Response:
    report = _load_report(report_id)
    return Response(content=report.model_dump_json(indent=2), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="editdiff-{report_id}.json"'})


def _discover_saved(v1_path: Path, v2_path: Path, evidence_dir: Path) -> DiscoverResponse:
    report = discover_changes(v1_path, v2_path, evidence_dir)
    temporary = DISCOVER_REPORTS / f"{report.report_id}.tmp"
    temporary.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(DISCOVER_REPORTS / f"{report.report_id}.json")
    return report


@app.post("/discover", response_model=DiscoverResponse)
async def discover(pre_final: UploadFile = File(...), final: UploadFile = File(...)) -> DiscoverResponse:
    report_id = uuid.uuid4().hex[:12]
    report_dir, evidence_dir = UPLOADS / report_id, EVIDENCE / report_id
    report_dir.mkdir(parents=True, exist_ok=False)
    evidence_dir.mkdir(parents=True, exist_ok=False)
    completed = False
    try:
        pre_path, final_path = report_dir / "pre_final.media", report_dir / "final.media"
        await _save(pre_final, pre_path)
        await _save(final, final_path)
        report = await run_in_threadpool(_discover_saved, pre_path, final_path, evidence_dir)
        completed = True
        return report
    except (MediaError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(422, "Could not decode uploaded videos within supported media limits.") from exc
    except FileNotFoundError as exc:
        raise HTTPException(503, "Required media processing service is unavailable.") from exc
    finally:
        await pre_final.close()
        await final.close()
        shutil.rmtree(report_dir)
        if not completed:
            shutil.rmtree(evidence_dir)


def _load_discover_report(report_id: str) -> DiscoverResponse:
    if not re.fullmatch(r"[0-9a-f]{12}", report_id):
        raise HTTPException(404, "Report not found")
    path = DISCOVER_REPORTS / f"{report_id}.json"
    if not path.is_file():
        raise HTTPException(404, "Report not found")
    return DiscoverResponse.model_validate_json(path.read_text(encoding="utf-8"))


@app.get("/discover/{report_id}", response_model=DiscoverResponse)
def get_discover_report(report_id: str) -> DiscoverResponse:
    return _load_discover_report(report_id)


@app.get("/discover/{report_id}/export")
def export_discover_report(report_id: str) -> Response:
    report = _load_discover_report(report_id)
    return Response(content=report.model_dump_json(indent=2), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="editdiff-discover-{report_id}.json"'})


def _release_gate_saved(requests: list[RevisionRequest], pre_final_path: Path, final_path: Path,
                        evidence_dir: Path) -> ReleaseGateResult:
    report = run_release_gate(requests, pre_final_path, final_path, evidence_dir)
    temporary = RELEASE_GATE_REPORTS / f"{report.report_id}.tmp"
    temporary.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(RELEASE_GATE_REPORTS / f"{report.report_id}.json")
    return report


@app.post("/release-gate", response_model=ReleaseGateResult)
async def release_gate(pre_final: UploadFile = File(...), final: UploadFile = File(...),
                       notes: str = Form(...)) -> ReleaseGateResult:
    if len(notes) > 20000:
        raise HTTPException(400, "Notes exceed 20,000 characters.")
    requests = parse_notes(notes)
    if not requests or len(requests) > 30:
        raise HTTPException(400, "Provide between 1 and 30 revision notes.")
    report_id = uuid.uuid4().hex[:12]
    report_dir, evidence_dir = UPLOADS / report_id, EVIDENCE / report_id
    report_dir.mkdir(parents=True, exist_ok=False)
    evidence_dir.mkdir(parents=True, exist_ok=False)
    completed = False
    try:
        pre_final_path = report_dir / "pre_final.media"
        final_path = report_dir / "final.media"
        await _save(pre_final, pre_final_path)
        await _save(final, final_path)
        report = await run_in_threadpool(
            _release_gate_saved, requests, pre_final_path, final_path, evidence_dir
        )
        completed = True
        return report
    except (MediaError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HTTPException(422, "Could not decode uploaded videos within supported media limits.") from exc
    except FileNotFoundError as exc:
        raise HTTPException(503, "Required media processing service is unavailable.") from exc
    finally:
        await pre_final.close()
        await final.close()
        shutil.rmtree(report_dir)
        if not completed:
            shutil.rmtree(evidence_dir)


def _load_release_gate_report(report_id: str) -> ReleaseGateResult:
    if not re.fullmatch(r"[0-9a-f]{12}", report_id):
        raise HTTPException(404, "Report not found")
    path = RELEASE_GATE_REPORTS / f"{report_id}.json"
    if not path.is_file():
        raise HTTPException(404, "Report not found")
    return ReleaseGateResult.model_validate_json(path.read_text(encoding="utf-8"))


@app.get("/release-gate/{report_id}", response_model=ReleaseGateResult)
def get_release_gate_report(report_id: str) -> ReleaseGateResult:
    return _load_release_gate_report(report_id)


@app.get("/release-gate/{report_id}/export")
def export_release_gate_report(report_id: str) -> Response:
    report = _load_release_gate_report(report_id)
    return Response(
        content=report.model_dump_json(indent=2), media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="editdiff-release-gate-{report_id}.json"'},
    )
