from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .models import AnalyzeResponse
from .notes import parse_notes
from .verifier import verify

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / ".data"
UPLOADS = DATA / "uploads"
EVIDENCE = DATA / "evidence"
UPLOADS.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="EditDiff API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/evidence", StaticFiles(directory=EVIDENCE), name="evidence")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


async def _save(upload: UploadFile, destination: Path) -> None:
    if not upload.filename:
        raise HTTPException(400, "Missing filename")
    with destination.open("wb") as f:
        shutil.copyfileobj(upload.file, f)


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    v1: UploadFile = File(...),
    v2: UploadFile = File(...),
    notes: str = Form(...),
) -> AnalyzeResponse:
    requests = parse_notes(notes)
    if not requests:
        raise HTTPException(400, "Add at least one revision note.")

    report_id = uuid.uuid4().hex[:12]
    report_dir = UPLOADS / report_id
    evidence_dir = EVIDENCE / report_id
    report_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    ext1 = Path(v1.filename or "v1.mp4").suffix or ".mp4"
    ext2 = Path(v2.filename or "v2.mp4").suffix or ".mp4"
    v1_path = report_dir / f"v1{ext1}"
    v2_path = report_dir / f"v2{ext2}"
    await _save(v1, v1_path)
    await _save(v2, v2_path)

    try:
        results = [verify(req, v1_path, v2_path, evidence_dir) for req in requests]
    except Exception as exc:
        raise HTTPException(422, f"Could not analyze uploaded media: {exc}") from exc

    for result in results:
        if result.evidence.v1_frame_path:
            result.evidence.v1_frame_path = f"/evidence/{report_id}/{Path(result.evidence.v1_frame_path).name}"
        if result.evidence.v2_frame_path:
            result.evidence.v2_frame_path = f"/evidence/{report_id}/{Path(result.evidence.v2_frame_path).name}"

    summary = {"PASS": 0, "FAIL": 0, "REVIEW": 0}
    for r in results:
        summary[r.verdict.value] += 1
    return AnalyzeResponse(report_id=report_id, summary=summary, results=results)
