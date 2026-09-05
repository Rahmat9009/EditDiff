# EditDiff

**Prove every revision landed.**

EditDiff compares a previous video export (V1), a revised export (V2), and one revision note per line. It returns PASS / FAIL / REVIEW with inspectable frames and measured evidence.

## Run locally

### Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Requires Python 3.11+ and `ffmpeg` / `ffprobe` on PATH. Run commands below from `editdiff/` unless otherwise stated.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## Backend architecture and evidence

FastAPI receives multipart uploads, validates media with ffprobe, and runs blocking media analysis in a worker thread. Notes become typed revision requests. FFmpeg extracts audio and JPEGs; OpenCV measures grayscale frame differences and ORB matches. A conservative decision layer combines those measurements with optional Gemini inspection.

The existing response fields are preserved. Added evidence includes methods, reason codes, thresholds, evidence-window bounds, timestamped frame URLs, semantic availability, model observations, cited frame indices, and signal agreement. Semantic frame indices are zero-based **pair indices** in the three same-timestamp V1/V2 pairs, not indices into the flattened `frames` list. Pause reports also include independently aligned flank frames with their actual V1/V2 timestamps.

Uploads use server-generated names within `.data/uploads/{report_id}` and are deleted after processing, including failed analyses. Completed JSON reports are atomically saved in `.data/reports/{report_id}.json`; images remain in `.data/evidence/{report_id}`. Reports survive server restarts while this directory is retained. Errors returned to clients omit internal paths and subprocess diagnostics.

## Deterministic checks

- **Mute:** Compare RMS over a two-second window around the note. PASS requires active V1 audio (>0.008 RMS), V2 below 0.004 RMS, and a V2/V1 ratio below 0.2. Merely reducing loudness cannot pass. Missing V1 audio returns REVIEW; removal of V2's audio track can satisfy a mute when V1 had active audio.
- **Pause removal:** Inspect up to six seconds around the requested V1 timestamp using 100 ms RMS bins. Find a silence interval containing the timestamp with active sound on both sides. Match two-frame visual anchors before and after that interval into V2 within +/-2.5 seconds. PASS requires unique low-error anchor matches, an offset change of at least 0.3 seconds consistent with the silence length, and reduced local silence. A shorter total export is never enough. Retained timing plus retained silence yields FAIL; ambiguous anchors, missing audio, or unbounded silence yield REVIEW.
- **Visual, B-roll, logo, blur, title, crop:** Sample timestamp -0.5, center, and +0.5 seconds, clipped to valid media bounds. Essentially unchanged samples (<0.002 mean normalized grayscale difference throughout) yield FAIL when not contradicted by semantic evidence. A changed image alone yields REVIEW. ORB matches are supporting metrics, not proof of the requested intent.
- **Missing/out-of-range timestamps and unsupported requests:** REVIEW. The engine never silently substitutes another moment.

Thresholds are recorded in each result. Confidence is a conservative **evidence-strength score**, not an empirically calibrated probability. Strong mute evidence scores 0.90; two-signal local cuts 0.86; semantic-plus-change PASS is capped at 0.88. Ambiguity/conflicts usually score 0.30-0.50 and return REVIEW. These fixed evidence tiers need calibration on real editor-labelled footage before statistical claims can be made.

## Optional semantic inspection

Set both environment variables in the backend process:

```powershell
$env:GEMINI_API_KEY = "your-key"
$env:GEMINI_MODEL = "your-enabled-Gemini-model-id"
```

No specific model availability is assumed. Gemini receives at most six resized JPEGs per visual request: three labelled V1/V2 pairs. It must report before/after observations, the requested after-state presence, visible replacement text, and supporting pair indices. The integration uses the [Google Gen AI SDK structured-response API](https://googleapis.github.io/python-genai/). The external call uses a 20-second HTTP timeout.

A missing key/model, API failure (including rate limits), malformed response, invalid confidence, or out-of-range cited index cannot create a semantic verdict. Changed visual requests remain REVIEW without semantic proof; independent deterministic mute/pause and unchanged-image checks continue. No live key is needed for the demo or automated tests.

For quoted notes such as `00:04 Change the title from 'DRAFT CUT' to 'LAUNCH DAY'`, old/new wording is extracted. PASS requires the model's observed after wording to equal the requested target after case/whitespace normalization, plus measurable change in a cited frame. Unquoted or ambiguous title targets stay REVIEW. Semantic PASS is blocked when deterministic frames are essentially unchanged. Explicit numeric crop percentages remain REVIEW because this implementation does not measure an exact geometric scale.

## API

`POST /analyze` remains multipart with unchanged field names:

- `v1`: previous video
- `v2`: revised video
- `notes`: one request per line

The original `report_id`, `summary`, `results`, request fields, verdict, confidence, and evidence fields retain their types and meanings.

Added endpoints:

- `GET /reports/{report_id}` returns the saved AnalyzeResponse.
- `GET /reports/{report_id}/export` downloads the same structure as JSON.
- `GET /evidence/{report_id}/{filename}` serves evidence JPEGs.
- `GET /health` returns service status (not a dependency readiness check).

Unknown/malformed report IDs return 404. Missing multipart fields return 422; empty uploads/notes or excessive note counts return 400; files over 250 MiB return 413; undecodable or unsupported-duration/resolution video returns 422. Limits: 30 notes, 20,000 note characters, 0.2-1800 seconds per video, at most 4K pixel area. Configure a reverse-proxy request-size limit for deployment: application file limits run after multipart parsing.

## Reproducible judge fixture

```bash
python scripts/make_demo_assets.py
# With the backend running:
curl -F "v1=@sample/demo-v1.mp4" -F "v2=@sample/demo-v2.mp4" -F "notes=<sample/edit-notes.txt" http://localhost:8000/analyze
```

On Windows PowerShell use `curl.exe`. The shell wrapper `scripts/make_demo_assets.sh` calls the same Python generator. Generated content is deterministic; encoded bytes can vary with codec/tool versions. V1 is 14 seconds and V2 is 13 seconds.

The single golden specification is [sample/golden-demo.json](sample/golden-demo.json): it owns the revision notes, per-note verdicts, and expected summary with Gemini disabled. The generator derives `sample/edit-notes.txt` from it and copies both videos and those notes into `frontend/public/demo/`. **Load demo** fetches those exact public files; it does not author its own notes or counts.

Use `python scripts/make_demo_assets.py --sync-only` to refresh public copies from an existing canonical sample without re-encoding. A custom `--output` directory does not overwrite the public demo. `npm run build` checks byte-for-byte fixture consistency before building. Backend tests assert the golden per-note verdicts and summary, as well as public asset identity.

The demo intentionally includes an unchanged B-roll request and visual edits needing semantic confirmation. REVIEW is the truthful outcome when exact intent is unproven. Live semantic results can differ; no live Gemini call is used for golden automated validation.

## Verification

```bash
cd backend
python -m pytest
python -m compileall -q app tests ../scripts/make_demo_assets.py
```

Tests use the checked-in fixture and installed FFmpeg/ffprobe, plus mocked semantic results; they explicitly remove Gemini configuration. Coverage includes parsing, text targets, confidence/fusion, semantic failure fallback, mute decisions, actual local pause cuts, misleading shorter exports, unchanged visuals, uploads, schema compatibility, image URLs, JSON persistence/export, and error cleanup. No backend formatter, linter, or type checker is configured in `pyproject.toml`.

Frontend validation (from `frontend/`):

```bash
npm install
npm run build
```

The frontend uses the real JSON export endpoint with a `.json` filename. It falls back to the report in browser memory only if the endpoint or response fails. Selected entries show evidence windows and semantic availability; raw methods, reasons, metrics and thresholds remain inside a disclosure.

## Current limits

This is a local hackathon service without authentication, background-job scheduling, retention cleanup, or distributed report storage. Protect it before public deployment. The backend exports JSON; the frontend also offers browser Print / PDF.

Visual and mute checks use the same requested timestamp in both exports; they do not globally align timelines after earlier edits. The pause detector alone estimates local offsets, at 100 ms resolution. Repeated/static footage, speed changes, larger shifts, pauses without clear audio flanks, subtle edits below image resolution, or revisions outside the sampled window can require human review. Small logo/text edits can be below the global difference threshold. Music removal while preserving speech needs source separation and is not proven by RMS. Three frames do not establish that an edit holds throughout an entire clip. Model text reading and intent interpretation remain fallible.
