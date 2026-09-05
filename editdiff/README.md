# EditDiff

**Prove every revision landed.**

EditDiff is an evidence-first revision QA tool for video creators and editors. Upload a previous export, revised export, and revision notes. It returns a PASS / FAIL / REVIEW ledger with timestamped before/after frames and deterministic audio/visual metrics.

## What works in this first build

- V1 + V2 video upload
- One-line-per-request edit note parser with timestamps
- Automatic check classification: mute, pause removal, text change, crop/zoom, visual change
- FFmpeg audio RMS evidence
- OpenCV frame-difference + feature-match evidence
- PASS / FAIL / REVIEW report
- Timestamped V1/V2 evidence frames
- Judge-ready Next.js report UI
- No AI/API dependency for the core demo

Gemini 3.8 Flash is the planned semantic layer for requests that deterministic signals cannot prove alone (for example, verifying the exact replacement title), but the core verifier remains deterministic.

## Run locally

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Requires `ffmpeg` and `ffprobe` on PATH.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## API

`POST /analyze` as multipart form data:

- `v1`: previous video
- `v2`: revised video
- `notes`: edit notes, one per line

## Next milestones

1. Gemini 3.8 semantic verifier for exact text/visual intent.
2. Localized pause-cut detector rather than total-duration heuristic.
3. Side-by-side synchronized video scrubber centered on evidence timestamp.
4. Downloadable/shareable audit report.
5. Synthetic 90-second demo fixture with guaranteed PASS + FAIL + REVIEW cases.
