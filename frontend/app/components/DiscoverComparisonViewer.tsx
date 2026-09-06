"use client";

import { useMemo } from "react";
import { timecode } from "../lib/format";
import type { ChangeKind } from "../lib/types";
import { ChangeKindBadge, KIND_GLYPH } from "./ChangeKindBadge";
import { ComparisonViewerCore } from "./ComparisonViewerCore";
import type { ViewerMarker } from "./TimelineRail";

export type DiscoverMarkerItem = {
  id: string;
  kind: ChangeKind;
  title: string;
  preFinalTime?: number | null;
  finalTime?: number | null;
  index: number;
};

type Props = {
  preFinalUrl: string | null;
  finalUrl: string | null;
  preFinalName?: string;
  finalName?: string;
  markers: DiscoverMarkerItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  seek: { preFinalTime: number; finalTime: number; nonce: number } | null;
  selectedChange: {
    kind: ChangeKind;
    title: string;
    preFinalTime?: number | null;
    finalTime?: number | null;
  } | null;
};

const KIND_ACCESSIBLE_NAME: Record<ChangeKind, string> = {
  VISUAL: "Visual change",
  TIMING: "Timing change",
  AUDIO: "Audio change",
  TEXT: "Text change",
  REVIEW: "Review needed",
};

export function DiscoverComparisonViewer({
  preFinalUrl,
  finalUrl,
  markers,
  selectedId,
  onSelect,
  seek,
  selectedChange,
}: Props) {
  const viewerMarkers: ViewerMarker[] = useMemo(() => {
    return markers.map((m) => {
      // Position on the final timeline; fallback to pre-final if final is not timed
      const sec = m.finalTime ?? m.preFinalTime ?? 0;
      const preTs = m.preFinalTime !== null && m.preFinalTime !== undefined ? timecode(m.preFinalTime) : null;
      const finalTs = m.finalTime !== null && m.finalTime !== undefined ? timecode(m.finalTime) : null;

      let timeLabel = finalTs ?? preTs ?? "00:00";
      if (preTs && finalTs && preTs !== finalTs) {
        timeLabel = `Pre-final ${preTs} · Final ${finalTs}`;
      }

      return {
        id: m.id,
        seconds: sec,
        label: m.title,
        index: m.index,
        tone: m.kind.toLowerCase(),
        glyph: KIND_GLYPH[m.kind] ?? "◈",
        tooltip: `${m.kind} · ${timeLabel} · ${m.title}`,
        accessibleText: `${KIND_ACCESSIBLE_NAME[m.kind] || m.kind} ${m.index} at ${timeLabel}: ${m.title}`,
      };
    });
  }, [markers]);

  const coreSeek = useMemo(() => {
    if (!seek) return null;
    return {
      aTime: seek.preFinalTime,
      bTime: seek.finalTime,
      nonce: seek.nonce,
    };
  }, [seek]);

  const captionElement = selectedChange ? (
    <p className="viewer__caption viewer__caption--discover">
      <ChangeKindBadge kind={selectedChange.kind} size="sm" />
      <span className="viewer__caption-text">{selectedChange.title}</span>
      <span className="viewer__caption-ts">
        {selectedChange.preFinalTime !== null && selectedChange.preFinalTime !== undefined &&
         selectedChange.finalTime !== null && selectedChange.finalTime !== undefined &&
         selectedChange.preFinalTime !== selectedChange.finalTime
          ? `PRE ${timecode(selectedChange.preFinalTime)} → FINAL ${timecode(selectedChange.finalTime)}`
          : timecode(selectedChange.finalTime ?? selectedChange.preFinalTime ?? 0)}
      </span>
    </p>
  ) : null;

  return (
    <ComparisonViewerCore
      v1Url={preFinalUrl}
      v2Url={finalUrl}
      v1Label="PRE-FINAL"
      v2Label="FINAL"
      v1AudioLabel="Hear Pre-final"
      v2AudioLabel="Hear Final"
      markers={viewerMarkers}
      selectedId={selectedId}
      onSelect={onSelect}
      seek={coreSeek}
      caption={captionElement}
      emptyMessage="Source files are no longer in memory. Re-select both exports to use the discovery view."
    />
  );
}
