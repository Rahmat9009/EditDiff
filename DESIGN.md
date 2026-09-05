---
name: EditDiff
description: Evidence-first revision QA for video teams — an editorial evidence console, not a dashboard.
colors:
  ink: "#11110f"
  ink-soft: "#34342e"
  muted: "#6b6a62"
  paper: "#f2f1ec"
  panel: "#f8f7f2"
  panel-sunk: "#edece5"
  line: "#d5d3c9"
  line-strong: "#b3b1a4"
  stage: "#0d0d0b"
  field: "#fffdf7"
  acid: "#d7ff3f"
  fail: "#ff5b45"
  review: "#f2b134"
  brand-slate: "#2c353c"
  brand-green: "#bcc14d"
typography:
  display:
    fontFamily: "Georgia, 'Times New Roman', serif"
    fontSize: "clamp(42px, 5.6vw, 76px)"
    fontWeight: 400
    lineHeight: 0.9
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Georgia, 'Times New Roman', serif"
    fontSize: "72px"
    fontWeight: 400
    lineHeight: 0.8
    letterSpacing: "normal"
  figure:
    fontFamily: "Georgia, 'Times New Roman', serif"
    fontSize: "20px"
    fontWeight: 400
    lineHeight: 1
    letterSpacing: "normal"
  title:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 700
    lineHeight: 1.5
    letterSpacing: "-0.01em"
  body:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
    fontSize: "10.5px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.14em"
  meta:
    fontFamily: "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0.03em"
rounded:
  none: "0"
  full: "50%"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  panel: "18px"
  gutter: "20px"
  section: "34px"
components:
  button-default:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "9px 14px"
  button-default-hover:
    backgroundColor: "{colors.acid}"
    textColor: "{colors.ink}"
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
    padding: "14px 22px"
  button-primary-hover:
    backgroundColor: "{colors.acid}"
    textColor: "{colors.ink}"
  button-primary-disabled:
    backgroundColor: "{colors.panel-sunk}"
    textColor: "{colors.ink-soft}"
  button-quiet:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.muted}"
    rounded: "{rounded.none}"
    padding: "9px 14px"
  verdict-pass:
    backgroundColor: "{colors.acid}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "5px 9px"
  verdict-fail:
    backgroundColor: "{colors.fail}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "5px 9px"
  verdict-review:
    backgroundColor: "{colors.review}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "5px 9px"
  panel:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.none}"
  filter-chip:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "6px 10px"
  filter-chip-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  input-notes:
    backgroundColor: "{colors.field}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "12px 14px"
  timeline-marker:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    height: "22px"
    width: "22px"
  stage:
    backgroundColor: "{colors.stage}"
    textColor: "{colors.paper}"
    rounded: "{rounded.none}"
---

# Design System: EditDiff

## Overview

**Creative North Star: "The Cutting Room Ledger"**

EditDiff looks like the bound audit book kept beside an edit bay. Two things are true at
once and the interface holds both: the craft of post-production, and the discipline of a
record that can be checked line by line. Warm off-white paper carries the reasoning —
requests, verdicts, measurements, timestamps — while the footage itself sits inside a
near-black viewing stage cut into that paper. Paper is where you think; the stage is where
you look. The interface never confuses the two.

The system is flat, ruled, and rectangular. There are no drop shadows anywhere, no rounded
cards, and no decorative surfaces. Depth comes from four tonal steps of the same warm
ground and from 1px hairlines, exactly as a printed ledger separates columns. Typography
does the ranking: a serif for anything that is a *finding* — the headline, the score, the
confidence figures — and a system sans for anything that is *operable*. A monospace carries
machine facts (timecodes, methods, thresholds), because those are values read digit by
digit, not prose.

One acid yellow-green is the only saturated color in the working interface, and it is
rationed. It marks the thing under examination: the verified verdict, the active control,
the moment currently in the transport. Two further hues exist and are reserved absolutely
for verdict semantics — never for decoration. The result should read as a professional
creative-production instrument: editorial, precise, technical, restrained, premium,
evidence-led, confident, operational. Not a SaaS dashboard, and not a developer tool.

**Key Characteristics:**

- Warm paper ground with a near-black viewing stage — two distinct worlds, never blended.
- Zero border radius on every rectangle; circles only where a control is genuinely round.
- Zero drop shadows. Depth is tonal layering plus 1px hairlines.
- Serif for findings, sans for controls, mono for machine values.
- One acid accent, rationed; two further hues locked to verdict meaning.
- Evidence-led hierarchy: what was requested, what happened, why we say so.

## Colors

A warm four-step paper ground and a near-black stage, interrupted by exactly one acid
accent and two verdict hues that are never used decoratively.

### Primary

- **Signal Acid** (`#d7ff3f`): The single high-energy accent. Reserved for attention,
  active comparison, verification, and detected difference — the PASS verdict, the hovered
  or active control, the wipe divider and its handle, the current position in the
  transport, and the accent bar in the app icon. It is never a background for a region,
  never a gradient, and never used to make something merely look lively.

### Secondary

- **Reject Red** (`#ff5b45`): FAIL only. The verdict badge, the timeline marker for a
  failed request, and the 4px inset rule on a failed ledger row. It appears nowhere else,
  so its presence always means one thing.
- **Hold Amber** (`#f2b134`): REVIEW only. The verdict badge, its timeline marker, the
  selected row rule, and the left rule on the "held for review" stance line. Amber is
  chosen deliberately over grey: REVIEW is a decision the system stands behind, not an
  absence of one.

### Neutral

- **Ink Black** (`#11110f`): Primary text, every 1px border on an interactive control,
  the primary button ground, and the active filter ground. Near-neutral and very slightly
  warm so it sits with the paper rather than against it.
- **Soft Ink** (`#34342e`): Explanatory body copy — verdict reasoning, the score call-out.
  One step back from Ink so long-form reasoning reads calmer than labels.
- **Muted Ink** (`#6b6a62`): Secondary and machine metadata — timecodes, kind labels,
  helper text, inactive segmented options. Measured at ~5.07:1 on Panel, so it clears
  WCAG AA for normal text; it is the floor, not a license to go lighter.
- **Warm Proof Paper** (`#f2f1ec`): The page ground. The warmth is the point — it reads as
  stock, not as a grey UI canvas.
- **Panel** (`#f8f7f2`): Raised working surfaces — intake, status, ledger, and every
  bordered container. One step lighter than the page.
- **Sunk Panel** (`#edece5`): Recessed surfaces — inline code, the disabled running state
  of the primary button. One step darker than the page.
- **Rule** (`#d5d3c9`): The default hairline. Container borders, dividers, table rules.
- **Strong Rule** (`#b3b1a4`): Hairlines that must survive against a busier field — the
  dashed empty drop zone, the notes field, segmented and filter borders.
- **Stage Black** (`#0d0d0b`): The video viewing stage and evidence frame ground only.
  Deeper than Ink so footage sits in a true black surround.
- **Field** (`#fffdf7`): The revision-notes textarea ground. The one surface lighter than
  Panel, marking the single place the user writes rather than reads.

### Brand

- **Brand Slate** (`#2c353c`): The outer registration frame of the EditDiff mark. A
  blue-leaning charcoal that belongs to the logo asset, **not** to the interface.
- **Brand Green** (`#bcc14d`): The inner crop bracket of the mark. A muted olive-green
  that is **not** Signal Acid. See Do's and Don'ts — these two values are asset colors and
  must not be introduced as UI tokens.

### Named Rules

**The Rationed Accent Rule.** Signal Acid marks what is being examined or verified —
attention, active comparison, detected difference. It is never sprayed for energy. If a
screen has acid in more than a few small places, one of them is decorative and should be
removed.

**The Locked Hue Rule.** Reject Red and Hold Amber belong to FAIL and REVIEW exclusively.
No error state, chart, tag, or illustration may borrow either. Their diagnostic value comes
entirely from never appearing for any other reason.

**The Two Grounds Rule.** Reasoning lives on paper; footage lives on Stage Black. Never
put a video on the paper ground, and never set body reasoning on the stage.

## Typography

**Display Font:** Georgia (with "Times New Roman", serif)
**Body Font:** system-ui (with -apple-system, "Segoe UI", Helvetica, Arial, sans-serif)
**Label/Mono Font:** ui-monospace (with SFMono-Regular, "SF Mono", Menlo, Consolas, monospace)

**Character:** A tight editorial serif carries every *finding* — the promise in the
headline, the score, each confidence figure. A neutral system sans carries everything
*operable* — labels, buttons, controls, reasoning. Monospace carries machine values that
are read digit by digit. The three are assigned by meaning, never by decoration, and the
split is what keeps the product from reading like a developer dashboard: the serif is
doing editorial work, not ornamental work.

### Hierarchy

- **Display** (400, `clamp(42px, 5.6vw, 76px)`, 0.9, -0.04em): The hero promise only, set
  in two lines with the word "revision" italic and underlaid by an acid highlight that
  starts at 62% of the line box, so it reads as marker over type rather than a filled box.
- **Headline** (400, 72px, 0.8): The single large numeral in the score panel — how many
  revisions the evidence verified. One per report.
- **Figure** (400, 19–24px): Serif numerals at working size — per-entry confidence, the
  report header tally counts, the source filename in a filled drop zone. Same voice as the
  headline, quieter.
- **Title** (700, 15–16px, -0.01em): Panel and section headings ("Intake", "Revision
  score", "Evidence ledger"). Sans, because a heading is a landmark, not a finding.
- **Body** (400, 15px, 1.5): Verdict reasoning and explanatory copy, set in Soft Ink and
  capped at 68ch so a paragraph of reasoning stays scannable.
- **Label** (700, 10.5px, 0.14em, uppercase): The micro-label voice used for every
  structural marker — panel eyebrows, drop-zone titles, the counter, disclosure summaries,
  figure captions. Wide tracking is what makes 10.5px legible and deliberate rather than
  small.
- **Meta** (400, 10–11px mono, 0.03–0.1em): Timecodes, report IDs, check kinds, and
  in-frame captions. Anything a machine produced and a human verifies.

### Named Rules

**The Findings-in-Serif Rule.** If a number or phrase is a *result* the system is
asserting, it is set in the serif. If it is a control, a label, or a landmark, it is sans.
A serif numeral in this product always means "this is what we found."

**The Wide-Micro Rule.** The 10.5px label voice is only legible because of 0.14em tracking
and 700 weight. Never set it tighter, lighter, or in sentence case.

## Layout

A centered shell of `min(1240px, 100% - 44px)` holds every section, so the page keeps one
consistent measure from masthead to footer. Inside it, the work is a two-column grid, and
the column ratio encodes priority: the intake workspace runs 1.85fr against a 1fr status
rail, while the report runs a near-even 1.05fr viewer against a 1fr ledger — evidence and
reasoning get comparable weight once results exist.

Vertical rhythm is deliberately tight rather than airy, because this is an Operate surface
where density is a feature: panels carry 18px internal padding, a 52px head, and a 20px
gutter (`--gap`) between grid children. Only the gutter is tokenized; the remaining rhythm
is observed convention that future work should follow rather than re-derive.

Two elements stick: the masthead at `top: 0`, and both the status panel and the report
viewer at `top: 86px`, so the comparison stage stays on screen while the ledger scrolls
beneath it. That stickiness is functional — selecting a revision must move the video the
user can still see.

**Responsive hierarchy** (laptop-first; the demo is recorded and judged on a laptop):

- **1440×900 — the primary target.** The entire intake must clear the fold: both export
  drop zones, all revision notes, and the Run revision audit button. Verified with the demo
  loaded, the button's lower edge lands at ~898px.
- **1280×800 — the short-laptop target.** A height-scoped rule
  (`min-width: 1081px and max-height: 860px`) compresses the hero, panel heads, drop
  zones, and thumbnails so the same four elements still clear an 800px fold. It must not
  affect taller viewports.
- **≤1080px.** Both two-column grids collapse to one column and the sticky panels go
  static, because a sticky element in a single column just eats the viewport.
- **~390px mobile.** The shell drops to `100% - 28px`, drop zones and evidence frame pairs
  stack, the ledger row reflows so the verdict, request, and confidence each take their own
  line, and the report tally wraps. Mobile stays clean and functional; it is not the demo
  target, but nothing may overflow horizontally.

### Named Rules

**The Fold Contract Rule.** On a 1440×900 laptop with the demo loaded, a judge must see
both exports, the revision notes, and the Run control without scrolling. Any change that
pushes the Run button below the fold at that size is a regression, not a style choice.

## Elevation & Depth

**This system has no drop shadows.** Not one. Depth is built two ways only:

1. **Tonal layering** across four steps of the same warm ground — Sunk Panel (`#edece5`),
   Warm Proof Paper (`#f2f1ec`), Panel (`#f8f7f2`), Field (`#fffdf7`) — plus Stage Black
   for footage. A surface reads as raised or recessed by its value, not by a cast shadow.
2. **1px hairlines** in Rule and Strong Rule. Every container, divider, and control is
   defined by a line, the way a printed table is.

The only `box-shadow` declarations in the system are *not* elevation. They are structural
marks that happen to use the property: a 4px inset left rule carrying a row's verdict, a
2px inset ring on a drag-active drop zone, and a 3px solid ring on the selected timeline
marker. None of them blur, and none of them imply a light source.

### Named Rules

**The No-Shadow Rule.** A blurred, offset shadow has no place in this product. If an
element needs separation, give it a hairline or move it one tonal step. `box-shadow` is
permitted only as a hard, unblurred inset rule or selection ring.

## Shapes

The form language is rectangular and unapologetic: **every rectangle in the system has a
0px radius.** Buttons, panels, badges, chips, inputs, frames, markers, and the stage are
all square-cornered. This is the single most identity-defining decision in the interface —
it is what makes the product read as an instrument and a printed record rather than a SaaS
app, and it is why no oversized pill or soft card can be introduced without destroying the
system.

Circles (`50%`) exist in exactly three places, all of them genuinely round objects: the
crosshair target in the empty score panel, the API status dot, and the wipe handle. A
circle here signals "an instrument part," never "a friendly shape."

Borders are always 1px. The one dashed border in the system marks the empty drop zone —
dashed because the region is a *slot awaiting a file*, and it becomes solid the moment
content lands.

### Named Rules

**The Square Corner Rule.** Radius is 0 for every rectangle, without exception. Circles are
reserved for round instrument parts. There is no middle radius in this system and none may
be added.

## Components

### Masthead

A sticky bar 66px tall on a translucent paper ground (`color-mix` 88%) with a 6px backdrop
blur and a bottom hairline, so ruled content scrolls under it without a hard edge. It
carries the mark, the wordmark, a hairline-divided claim ("Prove every revision landed."),
and an API status chip pushed right. The chip is a bordered label with a 7px dot — grey
while checking, green when online, and Reject Red with a red border when offline. It exists
because this product cannot function without its analysis service, and a user deserves to
know that before uploading two videos rather than after.

### Hero

A two-column band: the display promise and one lede line on the left, the verdict legend on
the right, on the shared paper ground with a bottom hairline. It is intentionally compact —
under 300px at the primary target — because the hero's job is to state the thesis and teach
the three-word vocabulary, then get out of the way of the tool. The legend is a definition
list pairing each verdict badge with its plain meaning; it teaches PASS/FAIL/REVIEW before
the user ever sees a result.

### Upload / Drop Zones

Two side-by-side regions divided by a 1px gap that reads as a rule. Each carries a mono
role badge (`V1`/`V2`) with an ink border and a micro-label title, so the two exports are
never confusable. Empty, the body is a dashed Strong Rule box with a hint and a call to
action. On drag-over the whole zone fills to 26% acid and gains a 2px inset ink ring —
unmistakable, and it uses the accent for exactly what the accent is for. Filled, it swaps
to a 132px 16:9 video thumbnail on Stage Black beside the filename in serif, with size,
duration, and dimensions in mono. Metadata that fails to read degrades to a warning line
rather than blocking the upload.

### Revision-Note Input

A monospace textarea on Field — the only surface lighter than Panel, marking it as the one
place the user writes. Monospace because notes are timestamped lines whose columns should
align. Its head pairs a micro-label with a live counter ("5 requests · 5 timestamped"),
which is the parse contract made visible: the user sees how many lines EditDiff recognized
and how many it could pin to a moment, before committing to a run. A helper line below
states the timestamp syntax and what happens without one.

### Analysis State

The status panel swaps to a staged progress list: a 3px sweeping indeterminate bar, the
current stage in serif, and a five-item list marking past, active, and future stages with a
small square dot. Stages advance on a timer and hold on the last one. A note states plainly
that stage timings are indicative and the audit finishes when the verifier returns. This
matters: the backend emits no progress events, so the UI must never imply a real percentage
it does not have.

### Report Header

The QA artifact's masthead. A single ruled bar carrying the section index, "Evidence
ledger", the report ID in mono, a tally (total requests plus each verdict count with its
badge), the two source filenames, and the Print and Export actions. The tally is separated
by a left hairline and exists so the headline result — 2 PASS / 1 FAIL / 2 REVIEW — is on
screen the instant results appear, rather than living only in a panel the user has scrolled
past. It wraps on narrow screens and drops its divider rule there.

### PASS / FAIL / REVIEW Badges

The most important component in the product. Each is a square, 1px ink-bordered inline
badge pairing a **monospace glyph with the verdict word**: PASS `✓` on Signal Acid, FAIL
`✕` on Reject Red, REVIEW `?` on Hold Amber. All three set their glyph and word in Ink.
Two sizes only.

All three clear WCAG AA against their own ground: PASS 16.44:1, REVIEW 10.00:1, FAIL
6.15:1. FAIL previously used white text at 3.07:1 and was corrected to Ink.

The glyph is not decoration — it is the accessibility contract. The verdict is the single
most important signal in the product, and its palette encodes meaning, so it must survive
monochrome printing, projection, and color-blind vision. Amber and a question mark are
chosen for REVIEW precisely so it reads as a deliberate, standing decision rather than a
missing or broken result.

### Evidence Ledger

A bordered stack of rows sharing hairline dividers. Each row's head is a four-column grid:
a mono index, the verdict badge, the request text with a mono meta line (timecode · check
kind · action hint), and the confidence figure in serif, right-aligned. The body carries
the requested target when the note quoted one (`DRAFT CUT → LAUNCH DAY` as bordered
chips), the plain-English reason, and — for REVIEW — an amber-ruled stance line stating
that EditDiff will not record a pass the evidence does not support.

Rows carry a 4px inset left rule that encodes state: transparent by default, a 55%-opacity
Reject Red on any FAIL even when unselected, and the full verdict hue when selected. A
failed revision is therefore visible while scanning, before anything is clicked. Selecting
a row expands its evidence window, semantic availability, and the paired before/after
frames, and drives the viewer to that timestamp.

Above the stack, four filter chips (All / PASS / FAIL / REVIEW) each carry their count;
the active chip inverts to ink with an acid count.

### Expandable Technical Evidence

A `<details>` disclosure with a micro-label summary and a `+`/`−` marker, opened by a top
hairline. Inside: methods, reason codes, thresholds, and a four-column metrics table
(Signal / V1 / V2 / Δ) with hairline row rules and mono numerals. This is the second tier
by design — the plain reason is always visible; the machine detail is one click away and
never leaks internal filesystem paths or subprocess diagnostics.

### Synchronized V1/V2 Viewer

A 16:9 Stage Black surface, split into two panes by default. Each pane is captioned
`V1 · BEFORE` and `V2 · AFTER`, with the V2 caption on acid so the revised cut is always
identifiable at a glance. A translucent caption bar at the top carries the selected
revision's verdict badge, text, and timecode, so a screenshot of the stage alone still
says what is being proven. Transport is a filled Play both button plus −1s / +1s steps.
Playback is locked to a V1 master clock; audio defaults to V2 with an explicit Hear V1 /
Hear V2 segmented control, because two videos playing two audio tracks is unusable.

### Timeline Markers

22px square buttons pinned along the rail at each revision's timestamp, each carrying its
verdict glyph and colored by verdict. The rail beneath is a 4px ink progress bar over a
hairline track with mono timecodes at both ends. Markers are the fastest path from "where
did things go wrong" to the evidence: the shape of the report is legible in one glance at
the rail. The selected marker takes a 3px solid ink ring and lifts slightly.

### Split / Wipe Comparison Controls

Two segmented fieldsets sharing one border-and-divider style: comparison mode
(Split / Wipe) and audio source (Hear V1 / Hear V2). The active option inverts to ink on
paper. In wipe mode, V2 is clipped by `inset()` against V1, with an acid divider line and a
30px circular acid grab handle at its center over a translucent stage fill — the handle
exists so the divider reads as draggable rather than as a stray rule. Split is the default
because it is the more reliable read; wipe is the closer look.

### Export / Report Actions

Two ghost buttons in the report header: Print / PDF and Export audit. Export fetches the
persisted JSON from the API and falls back to the in-memory report only on failure, stating
which path it used in a status note. The fallback is disclosed rather than silent, because
a QA artifact that quietly differs from the server's record would undermine the product's
entire premise.

## Do's and Don'ts

### Do:

- **Do** keep every rectangle at 0 radius and reserve `50%` circles for genuinely round
  instrument parts (the crosshair, the status dot, the wipe handle).
- **Do** convey depth with the four tonal ground steps and 1px hairlines, never with a
  blurred shadow.
- **Do** ration Signal Acid to attention, active comparison, verification, and detected
  difference — the verified verdict, the active control, the current transport position.
- **Do** pair every verdict with its monospace glyph (`✓` `✕` `?`) and its word. Color is
  never the only carrier.
- **Do** present REVIEW as a standing decision: amber, deliberate, with a stance line. It
  is the product's spine, not a degraded state.
- **Do** set findings in the serif and controls in the sans; put machine values in mono.
- **Do** keep both exports, the notes, and the Run control above the fold at 1440×900.
- **Do** state honestly when a capability is unavailable ("Semantic inspection unavailable;
  this verdict uses measured evidence only") without naming it as an error or a failure.
- **Do** keep motion functional: 0.14–0.15s state transitions, a 0.35–0.4s `rise` on
  results arriving, the indeterminate analysis sweep, and the smooth scroll that reveals a
  finished report. Everything honors `prefers-reduced-motion`.

### Don't:

- **Don't** introduce generic SaaS card grids, oversized pills, or any middle border
  radius. The square corner is the identity.
- **Don't** use purple AI gradients, glassmorphism, chat UI, sparkles, or robot/brain
  imagery. EditDiff measures video; it does not generate content and must not dress like a
  product that does.
- **Don't** add decorative dashboards, fake analytics, or charts that visualize nothing
  measured. Every number shown must come from the report.
- **Don't** use cyberpunk styling or neon-on-black surfaces. Stage Black is for footage
  only.
- **Don't** borrow Reject Red or Hold Amber for any non-verdict purpose, and don't use
  Signal Acid as a large fill or a gradient.
- **Don't** introduce Brand Slate (`#2c353c`) or Brand Green (`#bcc14d`) as interface
  tokens. They belong to the logo asset; the UI's ink and acid are separate values.
- **Don't** add entrance animations, parallax, or any motion that delays the demo. Nothing
  should stand between Run revision audit and the result.
- **Don't** present confidence as a probability or add accuracy claims — it is an
  uncalibrated evidence-strength score.
- **Don't** describe the bundled demo footage as real client work, or add customer names,
  testimonials, or usage statistics.

## Brand Mark

The official EditDiff mark is `editdiff/Logo.png`: two offset registration frames — a Brand
Slate outer crop frame and a Brand Green inner bracket — held apart over a grey field. The
geometry is the idea. Offset frames are what before-and-after, alignment, comparison, and
revision detection look like as a shape, which is why the mark suits an evidence product
rather than merely decorating it.

- **Primary usage.** Two assets ship under `frontend/public/brand/`:
  `editdiff-logo-source.png` is the untouched original and remains the source of truth, and
  `editdiff-mark.png` is the production presentation used in the product. The production
  cut is a **pixel-position-identical recolour** of the source — every pixel keeps its
  coordinates; only its colour is remapped, so the geometry is provably unaltered. Slate
  becomes Ink, olive becomes Signal Acid, the cool grey field becomes Strong Rule, and the
  white surround becomes transparent so the mark sits on any ground. Do not rotate, redraw,
  or adjust the offset — the offset *is* the meaning.
- **Clear space.** Keep free space on all sides equal to the width of the outer frame arm
  (roughly 1/8 of the mark's width). The asset already carries a white margin; do not crop
  into it.
- **Minimum practical size.** 40px, and even there the mark reads as a framed tile rather
  than as two resolvable offset frames; the acid bracket does not register. The masthead
  ships at 40px paired with the wordmark, which carries recognition. Treat 40px as the
  floor for the full mark and commission a simplified cut for anything smaller.
- **Reversed / dark-background usage.** No reversed cut exists. Brand Slate is too close to
  Stage Black to survive on it. Until a light-frame variant is produced, place the mark on
  paper or white only.
- **Favicon / app icon.** The shipped `frontend/app/icon.svg` is an `ED` monogram and is
  **legacy**; it must not guide future visual work. It remains the favicon only because the
  official mark has no small-size cut — at 16–32px the offset geometry does not resolve.
  Producing a simplified favicon variant is an open production task, not a license to
  improvise new geometry.
- **Mark versus wordmark.** The mark earns its place where identity is the message: the
  masthead, an exported or printed report header, an app icon. Inside the working
  interface, the product name alone is enough — the ledger should carry evidence, not
  branding.
