# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Video creators, editors, creative teams, agencies, and clients reviewing revisions.

The product is deliberately two-sided and no single primary user has been narrowed:
the same audit is useful to the person who wrote the revision notes and to the editor
who executed them. Both arrive with the same question — did the requested change
actually land — from opposite ends of the handoff.

## Product Purpose

EditDiff compares a previous video export (V1) against a revised export (V2), read
against the revision notes that were given to the editor, and proves whether each
requested revision actually landed.

Each request returns one of three verdicts — PASS, FAIL, or REVIEW — with a
timestamp, the measured signals behind the decision, and inspectable before/after
frames. Success is a reviewer trusting the ledger enough to act on it: sign off, or
send specific items back.

## Positioning

An evidence-first revision QA tool, not an AI content generator. EditDiff does not
create, edit, or suggest video; it measures two exports against a written request and
reports what the evidence supports.

The mechanism a neighboring product could not truthfully copy is the refusal itself:
REVIEW is a first-class, intentional outcome. When the available evidence cannot
establish whether a requested edit landed, EditDiff records that rather than
manufacturing a pass. Verdicts carry their thresholds, methods, and reason codes, so
a decision can be audited rather than trusted on faith.

## Operating Context

- A reviewer sends an editor a list of revision notes, one request per line, usually
  timestamped (`00:04 Change the title from 'DRAFT CUT' to 'LAUNCH DAY'`).
- A revised export comes back. The reviewer must decide whether to approve it or
  return it, often without time to scrub both cuts end to end.
- The audit is the artifact that moves between the two sides: a ledger of requests,
  verdicts, timestamps and evidence that either party can inspect or export.
- Work is per-comparison and stateless from the user's point of view: two files and a
  block of notes in, one report out. There is no project, library, or account.

**Critical demo path** (the sequence the product is judged on):
Load Demo → Run Revision Audit → 2 PASS / 1 FAIL / 2 REVIEW → select a revision →
synchronized V1/V2 proof at that timestamp → export the report.

## Capabilities and Constraints

**Verdict vocabulary.** PASS (evidence supports the requested revision), FAIL
(evidence contradicts it), REVIEW (available evidence cannot establish either).
These three terms are product-level, not UI labels, and appear in the API, the
report, and the export.

**Terminology.** V1 = previous export; V2 = revised export; a *revision note* or
*request* is one line of the notes; a *verdict* applies to one request; the full set
is a *report*, identified by a `report_id`.

**Deterministic checks** cover mute, pause removal, and visual change (B-roll, logo,
blur, title, crop) via audio RMS, grayscale frame difference, and ORB feature
matching. Thresholds are recorded in every result.

**Semantic inspection is optional and additive.** An external model layer can confirm
exact intent (for example, quoted title wording). It is disabled by default, requires
configuration, and cannot manufacture a verdict on its own: a missing key, API
failure, malformed response, or out-of-range citation leaves deterministic results
untouched. The product must read as complete and intentional with no key present —
the canonical demo runs this way, and REVIEW there is the truthful outcome, not a
degraded one. *Open: whether semantic inspection should eventually become the
default or required path is undecided.*

**Confidence is an evidence-strength score, not a calibrated probability.** It must
not be presented as a statistical likelihood until calibrated on real editor-labelled
footage.

**Known analysis limits** that future work must not paper over: checks sample the
same requested timestamp in both exports and do not globally realign timelines after
earlier edits; only the pause detector estimates local offset, at 100 ms resolution;
three sampled frames do not prove an edit holds across a whole clip; small logo or
text edits can fall below the global difference threshold; music removal that
preserves speech is not provable by RMS; model text reading remains fallible.

**Service limits.** 30 notes, 20,000 note characters, 0.2–1800 s per video, 250 MiB
per file, at most 4K pixel area.

**Not built, deliberately.** No authentication, background job scheduling, retention
cleanup, or distributed report storage. This is a local service and must be protected
before public deployment.

*Open: the product's trajectory after the hackathon — demo artifact, real product, or
portfolio piece — is undecided. Future work should not assume a direction.*

## Brand Commitments

Name: **EditDiff**. Claim: **"Prove every revision landed."**

Visual character the user has made binding:

- Premium post-production software; editorial; precise.
- Technical without looking like a developer dashboard.
- Quiet confidence. High information clarity.
- Near-black / warm off-white foundation with one restrained high-energy acid accent.
- Strong typography, hairline rules, evidence-led hierarchy.

Explicitly ruled out: generic SaaS cards; purple AI gradients; glassmorphism; chatbot
styling; sparkles; robot or brain AI imagery; oversized rounded cards; meaningless
analytics; over-animation.

Voice: plain, creator-facing, and claim-free. State what was measured and what it
supports. No marketing fluff, no "AI-powered" framing, no capability the evidence
does not demonstrate.

**Two marks currently exist and have not been reconciled:**

- `editdiff/frontend/app/icon.svg` — an `ED` monogram, acid on near-black. Shipped as
  the favicon and echoed by the masthead badge in the running app.
- `editdiff/Logo.png` — two offset registration/crop brackets, dark slate over grey
  with an acid-green inner bracket, reading as two frames held in comparison.

*Open: which is the official mark, and whether the second is binding, is unconfirmed.
Future work must not assume one supersedes the other, and must not restyle either
into a new identity without asking.*

## Evidence on Hand

- **Canonical golden fixture** — `sample/golden-demo.json` owns the demo's revision
  notes, per-note verdicts, and expected summary with semantic inspection disabled:
  **2 PASS / 1 FAIL / 2 REVIEW**. It is the single source of truth; the generator
  derives `sample/edit-notes.txt` from it and copies assets to
  `frontend/public/demo/`. Backend tests and the frontend build both assert against
  it. Counts must never be hardcoded in the UI.
- **Demo media** — `sample/demo-v1.mp4` (14 s) and `sample/demo-v2.mp4` (13 s),
  deterministically generated by `scripts/make_demo_assets.py`. Synthetic, not real
  client footage.
- **Backend test suite** — covers note parsing, text targets, confidence fusion,
  semantic failure fallback, mute decisions, real local pause cuts, misleading
  shorter exports, unchanged visuals, uploads, schema compatibility, image URLs, JSON
  persistence and export, and error cleanup.
- **Real API surface** — `POST /analyze`, `GET /reports/{id}`,
  `GET /reports/{id}/export`, `GET /evidence/{id}/{file}`, `GET /health`.
- **Brand assets** — `editdiff/frontend/app/icon.svg` (shipped) and
  `editdiff/Logo.png` (present, status unconfirmed; see Brand Commitments).

**Absences future work must not fabricate:** there are no customers, testimonials,
case studies, press mentions, usage statistics, benchmarks, pricing, or accuracy
claims. The demo footage is synthetic and must not be presented as real client work.
No named client or agency may appear in any surface.

## Product Principles

1. **Never turn uncertainty into a fake PASS.** PASS, FAIL, and REVIEW must stay
   trustworthy. REVIEW is a correct answer, presented as intentional rigor, never as
   an error or a missing feature.
2. **Every verdict shows its work.** A decision is only as good as the evidence a
   user can inspect: timestamp, method, measured signals, and before/after frames.
3. **Measure; do not generate.** EditDiff reports on video it is given. It does not
   author, alter, or recommend edits.
4. **Degrade honestly.** Missing optional capability reduces what can be claimed, not
   whether the product works. Absent semantic inspection, the tool remains complete.
5. **Claim only what is demonstrated.** No statistical language for uncalibrated
   scores, no invented proof, no capability the code does not have.

## Accessibility & Inclusion

The three verdicts must never be distinguishable by color alone. Each carries a
non-color cue (PASS ✓, FAIL ✕, REVIEW ?) alongside its text label, because the
verdict is the single most important signal in the product and its palette encodes
meaning. Standard keyboard operability and visible focus apply to the full audit
path — load, run, select a revision, inspect evidence, export.
