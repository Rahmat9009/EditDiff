"use client";

import { useMemo } from "react";
import { previewNotes } from "../lib/notes";
import { timecode } from "../lib/format";
import { DropZone, type MediaMeta, type MediaSlot } from "./DropZone";

export const NOTES_PLACEHOLDER = "Add a timestamp and requested edit, one request per line.";

type Props = {
  v1: MediaSlot | null;
  v2: MediaSlot | null;
  v1Meta: MediaMeta | null;
  v2Meta: MediaMeta | null;
  notes: string;
  busy: boolean;
  demoBusy: boolean;
  error: string;
  onSelect: (role: "v1" | "v2", file: File | null) => void;
  onMeta: (role: "v1" | "v2", meta: MediaMeta | null) => void;
  onNotes: (value: string) => void;
  onRun: () => void;
  onLoadDemo: () => void;
};

export function IntakePanel({
  v1,
  v2,
  v1Meta,
  v2Meta,
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
  const ready = !!v1 && !!v2 && parsed.length > 0;

  return (
    <form
      className="panel intake"
      onSubmit={(e) => {
        e.preventDefault();
        onRun();
      }}
    >
      <div className="panel__head">
        <span className="panel__index">01</span>
        <h2>Intake</h2>
        <button type="button" className="btn btn--demo" onClick={onLoadDemo} disabled={busy || demoBusy}>
          {demoBusy ? "Loading demo…" : "Load demo"}
        </button>
      </div>

      <div className="intake__drops">
        <DropZone
          role="V1"
          title="Previous export"
          hint="The cut your editor was working from."
          slot={v1}
          meta={v1Meta}
          disabled={busy || demoBusy}
          onSelect={(f) => onSelect("v1", f)}
          onMeta={(m) => onMeta("v1", m)}
        />
        <DropZone
          role="V2"
          title="Revised export"
          hint="The cut that came back after your notes."
          slot={v2}
          meta={v2Meta}
          disabled={busy || demoBusy}
          onSelect={(f) => onSelect("v2", f)}
          onMeta={(m) => onMeta("v2", m)}
        />
      </div>

      <div className="intake__notes">
        <div className="intake__notes-head">
          <label htmlFor="revision-notes">Revision notes — one request per line</label>
          <span className="counter">
            {parsed.length} request{parsed.length === 1 ? "" : "s"} · {timed} timestamped
          </span>
        </div>
        <textarea
          id="revision-notes"
          value={notes}
          rows={7}
          spellCheck={false}
          disabled={busy || demoBusy}
          placeholder={NOTES_PLACEHOLDER}
          onChange={(e) => onNotes(e.target.value)}
          aria-describedby="notes-help"
        />
        <p className="intake__help" id="notes-help">
          Start a line with a timestamp (<code>00:06</code> or <code>6s</code>) to pin the check to
          that moment. Missing or out-of-range timestamps return REVIEW.
        </p>
        {parsed.length > 0 ? (
          <ul className="chips" aria-label="Parsed requests">
            {parsed.slice(0, 6).map((p, i) => (
              <li key={`${p.text}-${i}`}>
                <span>{p.seconds === null ? "no ts" : timecode(p.seconds)}</span>
                {p.text.replace(/^\s*(?:\d{1,2}:)?\d{1,2}:\d{2}(?:\.\d+)?\s*/, "")}
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <div className="intake__foot">
        <button className="btn btn--run" type="submit" disabled={busy || demoBusy || !ready}>
          {busy ? "Auditing…" : "Run revision audit"}
          <span aria-hidden="true">→</span>
        </button>
        {!ready && !busy ? (
          <p className="intake__requirement">
            Add both exports and at least one revision note to run an audit.
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
