"use client";

import { DropZone, type MediaMeta, type MediaSlot } from "./DropZone";

type Props = {
  preFinal: MediaSlot | null;
  final: MediaSlot | null;
  preFinalMeta: MediaMeta | null;
  finalMeta: MediaMeta | null;
  busy: boolean;
  error: string;
  onSelect: (role: "v1" | "v2", file: File | null) => void;
  onMeta: (role: "v1" | "v2", meta: MediaMeta | null) => void;
  onRun: () => void;
};

export function DiscoverIntakePanel({
  preFinal,
  final,
  preFinalMeta,
  finalMeta,
  busy,
  error,
  onSelect,
  onMeta,
  onRun,
}: Props) {
  const ready = !!preFinal && !!final;

  return (
    <form
      className="panel intake intake--discover"
      onSubmit={(e) => {
        e.preventDefault();
        onRun();
      }}
    >
      <div className="panel__head">
        <span className="panel__index">01</span>
        <h2>Intake · Discover changes</h2>
      </div>

      <div className="intake__drops">
        <DropZone
          role="PRE-FINAL"
          title="Pre-final export"
          hint="The version immediately before the final delivery."
          slot={preFinal}
          meta={preFinalMeta}
          disabled={busy}
          onSelect={(f) => onSelect("v1", f)}
          onMeta={(m) => onMeta("v1", m)}
        />
        <DropZone
          role="FINAL"
          title="Final export"
          hint="The version sent for review or delivery."
          slot={final}
          meta={finalMeta}
          disabled={busy}
          onSelect={(f) => onSelect("v2", f)}
          onMeta={(m) => onMeta("v2", m)}
        />
      </div>

      <div className="intake__discover-info">
        <p className="intake__discover-lead">
          Compare two exports and build a timestamped ledger of meaningful visual, timing, and audio differences.
        </p>
        <p className="intake__discover-sub">
          No revision notes required. EditDiff aligns the timelines, bounds temporal drift, and extracts verifiable evidence frames.
        </p>
      </div>

      <div className="intake__foot">
        <button className="btn btn--run" type="submit" disabled={busy || !ready}>
          {busy ? "Discovering…" : "Find changes"}
          <span aria-hidden="true">→</span>
        </button>
        {!ready && !busy ? (
          <p className="intake__requirement">
            Add both the pre-final and final exports to discover changes.
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
