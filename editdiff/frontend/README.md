# EditDiff — web client

The creator-facing QA console for EditDiff. Next.js (App Router) + React, no UI
framework and no runtime dependencies beyond Next itself.

```bash
npm install
npm run dev     # http://localhost:3000
npm run build   # type-checks and builds
```

The API base URL comes from `NEXT_PUBLIC_API_URL` (default
`http://localhost:8000`). Nothing secret belongs in this package — every
`NEXT_PUBLIC_*` value ships to the browser.

## The 60-second demo path

1. **Load demo** — loads the generated public copies of both canonical videos and
   `edit-notes.txt`. See [the golden specification](../sample/golden-demo.json) for the
   authoritative notes and expected no-Gemini verdicts. No file picker.
2. **Run revision audit** — staged progress while the verifier works.
3. **Revision score** — how many requested revisions the evidence supports.
4. **Click a PASS** — both exports jump to that timestamp with before/after frames.
5. **Click the FAIL** at `00:08` — the requested b-roll swap never landed.
6. **REVIEW** — EditDiff refuses to claim certainty the signals do not support.

## Structure

```
app/
  page.tsx                 state owner: files, notes, report, selection, export
  layout.tsx  globals.css  design system (paper / ink / one acid accent)
  lib/
    types.ts               POST /analyze contract + runtime response guard
    api.ts                 fetch wrappers, asset URLs, persisted JSON audit export
    format.ts              timecode, metric and verdict formatting
    notes.ts               client preview of the note parser
  components/
    SiteHeader  Hero  IntakePanel  DropZone       intake
    StatusPanel  AnalysisStages                   score + staged progress
    ReportSection  EvidenceEntry  EvidenceFrame   evidence ledger
    ComparisonViewer  TimelineRail                synchronised comparison
    MetricTable  VerdictBadge
```

## Contract notes

`types.ts` requires only the frozen fields (`report_id`, `summary`, `results[]`
with `request`, `verdict`, `confidence`, `evidence`). Anything else the backend
adds is optional:

- `evidence.semantic` (or `semantic_result` / `semantic_evidence`) renders a
  semantic-check block inside an entry when present.
- `report.generated_at` is shown in the report bar when present.
- **Export audit** downloads `/reports/{id}/export` as `editdiff-{id}.json`.
  Only a real request/response failure uses the client-side JSON fallback.
- Evidence windows, semantic availability and observations appear in selected entries.
  Methods, reason codes, metrics and thresholds stay behind a disclosure.
- `npm run check:demo` verifies public assets against the canonical sample and runs
  automatically before builds. Regenerate or sync using the root demo script;
  never hand-edit the public copies.

`isReport()` rejects malformed payloads so a bad response surfaces as an error
message instead of a blank screen.

## Behaviour worth knowing

- **Object URLs** are created once per selected file and revoked on replace,
  clear and unmount. The comparison viewer reuses the same URLs, so video blobs
  are never duplicated.
- **Sync** — V1 is the master clock; V2 is corrected whenever it drifts more
  than 180 ms. Play, pause, scrub and marker jumps drive both elements.
  Paired playback stops at the shorter export; replay starts both from zero.
- **Progress** stages are indeterminate and hold on the last stage. The UI never
  claims a check finished before the report arrives.
- **Verdicts** are never colour-only: each carries its label and a glyph
  (`✓ ✕ ?`).
- Handled failure modes: API offline, analysis error, missing files, malformed
  response, unreadable video metadata, undecodable video, missing evidence frames.
