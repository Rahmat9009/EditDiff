"use client";

import { useMemo } from "react";
import { timecode } from "../../lib/format";
import { ComparisonViewerCore } from "../ComparisonViewerCore";
import type { ViewerMarker } from "../TimelineRail";

export type GateMarker = {
  /** Group-prefixed so a revision, a change and a check can share an id. */
  id: string;
  seconds: number;
  tone: string;
  glyph: string;
  label: string;
  group: string;
  index: number;
};

type Props = {
  baselineUrl: string | null;
  candidateUrl: string | null;
  markers: GateMarker[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  seek: { baselineTime: number; candidateTime: number; nonce: number } | null;
  caption: { label: string; group: string; tone: string; seconds: number | null } | null;
};

export function ReleaseGateComparisonViewer({
  baselineUrl,
  candidateUrl,
  markers,
  selectedId,
  onSelect,
  seek,
  caption,
}: Props) {
  const viewerMarkers: ViewerMarker[] = useMemo(
    () =>
      markers.map((m) => ({
        id: m.id,
        seconds: m.seconds,
        label: m.label,
        index: m.index,
        tone: m.tone,
        glyph: m.glyph,
        tooltip: `${m.group} · ${timecode(m.seconds)} · ${m.label}`,
        accessibleText: `${m.group} ${m.index} at ${timecode(m.seconds)}: ${m.label}`,
      })),
    [markers],
  );

  const coreSeek = useMemo(
    () =>
      seek ? { aTime: seek.baselineTime, bTime: seek.candidateTime, nonce: seek.nonce } : null,
    [seek],
  );

  const captionElement = caption ? (
    <p className="viewer__caption viewer__caption--gate">
      <span className={`viewer__caption-group viewer__caption-group--${caption.tone}`}>
        {caption.group}
      </span>
      <span className="viewer__caption-text">{caption.label}</span>
      {caption.seconds !== null ? (
        <span className="viewer__caption-ts">{timecode(caption.seconds, true)}</span>
      ) : null}
    </p>
  ) : null;

  return (
    <ComparisonViewerCore
      v1Url={baselineUrl}
      v2Url={candidateUrl}
      v1Label="BASELINE"
      v2Label="RELEASE CANDIDATE"
      v1AudioLabel="Hear baseline"
      v2AudioLabel="Hear candidate"
      timelineSource="b"
      markers={viewerMarkers}
      selectedId={selectedId}
      onSelect={onSelect}
      seek={coreSeek}
      caption={captionElement}
      emptyMessage="Source files are no longer in memory. Re-select both exports to inspect the gate evidence."
    />
  );
}
