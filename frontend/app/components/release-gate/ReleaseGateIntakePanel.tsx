"use client";

import { useMemo } from "react";
import { previewNotes } from "../../lib/notes";
import { DropZone, type MediaMeta, type MediaSlot } from "../DropZone";

type Props = {
  baseline: MediaSlot | null;
  candidate: MediaSlot | null;
  baselineMeta: MediaMeta | null;
  candidateMeta: MediaMeta | null;
  notes: string;
  busy: boolean;
  demoBusy: boolean;
  error: string;
  onSelect: (role: "baseline" | "candidate", file: File | null) => void;
  onMeta: (role: "baseline" | "candidate", meta: MediaMeta | null) => void;
  onNotes: (value: string) => void;
  onRun: () => void;
  onLoadDemo: () => void;
};

export function ReleaseGateIntakePanel({
  baseline,
  candidate,
  baselineMeta,
  candidateMeta,
  notes,
  busy,
  demoBusy,
  error,
  onSelect,
  onMeta,
  onNotes,
  onRun,
  onLoadDemo,
}: Props) {
  const parsed = useMemo(() => previewNotes(notes), [notes]);
  const timed = parsed.filter((p) => p.seconds !== null).length;
  const ready = !!baseline && !!candidate;

  return (
    <form
      className="panel intake intake--gate"
      onSubmit={(e) => {
        e.preventDefault();
        onRun();
      }}
    >
      <div className="panel__head">
        <span className="panel__index">01</span>
        <h2>Intake · Release candidate</h2>
        <button
          type="button"
          className="btn btn--demo"
          onClick={onLoadDemo}
          disabled={busy || demoBusy}
        >
          {demoBusy ? "Loading demo…" : "Load demo"}
        </button>
      </div>

      <div className="intake__drops">
        <DropZone
          role="BASELINE"
          title="Baseline / pre-final"
          hint="The approved cut this release candidate came from."
          slot={baseline}
          meta={baselineMeta}
          disabled={busy || demoBusy}
          onSelect={(f) => onSelect("baseline", f)}
          onMeta={(m) => onMeta("baseline", m)}
        />
        <DropZone
          role="CANDIDATE"
          title="Release candidate / final"
          hint="The export you are about to publish."
          slot={candidate}
          meta={candidateMeta}
          disabled={busy || demoBusy}
          onSelect={(f) => onSelect("candidate", f)}
          onMeta={(m) => onMeta("candidate", m)}
        />
      </div>

      <div className="intake__notes">
        <div className="intake__notes-head">
          <label htmlFor="gate-notes">Revision notes — one request per line</label>
          <span className="counter">
            {parsed.length} request{parsed.length === 1 ? "" : "s"} · {timed} timestamped
          </span>
        </div>
        <textarea
          id="gate-notes"
          value={notes}
          rows={5}
          spellCheck={false}
          disabled={busy || demoBusy}
          placeholder="Add a timestamp and requested edit, one request per line."
          onChange={(e) => onNotes(e.target.value)}
          aria-describedby="gate-notes-help"
        />
        <p className="intake__help" id="gate-notes-help">
          Notes tell the gate which changes were <b>asked for</b>. Changes the gate detects that no
          note accounts for are reported as unexpected. Without notes every detected change is
          assessed without a requested-revision baseline.
        </p>
      </div>

      <div className="intake__foot">
        <button className="btn btn--run btn--gate" type="submit" disabled={busy || !ready}>
          {busy ? "Running release gate…" : "Run Release Gate"}
          <span aria-hidden="true">→</span>
        </button>
        {!ready && !busy ? (
          <p className="intake__requirement">
            Add the baseline and the release candidate to run the gate.
          </p>
        ) : null}
      </div>

      {error ? (
        <p className="alert" role="alert">
          {error}
        </p>
      ) : null}
    </form>
  );
}
