"use client";

import { timecode, VERDICT_GLYPH } from "../lib/format";
import type { Verdict } from "../lib/types";

export type ViewerMarker = {
  id: string;
  seconds: number;
  label: string;
  index: number;
  verdict?: Verdict;
  tone?: string;
  glyph?: string;
  tooltip?: string;
  accessibleText?: string;
};

export type Marker = ViewerMarker;

type Props = {
  duration: number;
  currentTime: number;
  markers: ViewerMarker[];
  selectedId: string | null;
  onScrub: (seconds: number) => void;
  onSelect: (id: string) => void;
};

export function TimelineRail({
  duration,
  currentTime,
  markers,
  selectedId,
  onScrub,
  onSelect,
}: Props) {
  const safeDuration = duration > 0 ? duration : 0;
  const pct = (seconds: number) =>
    safeDuration > 0 ? `${Math.min(Math.max(seconds / safeDuration, 0), 1) * 100}%` : "0%";

  return (
    <div className="rail">
      <div className="rail__markers">
        {safeDuration > 0
          ? markers.map((m) => {
              const tone = (m.tone ?? m.verdict ?? "review").toLowerCase();
              const glyph = m.glyph ?? (m.verdict ? VERDICT_GLYPH[m.verdict] : "•");
              const tooltip =
                m.tooltip ??
                (m.verdict
                  ? `${timecode(m.seconds)} · ${m.verdict} · ${m.label}`
                  : `${timecode(m.seconds)} · ${m.label}`);
              const accessibleText =
                m.accessibleText ??
                (m.verdict
                  ? `Revision ${m.index} at ${timecode(m.seconds)}, ${m.verdict}: ${m.label}`
                  : `Change ${m.index} at ${timecode(m.seconds)}: ${m.label}`);

              return (
                <button
                  key={m.id}
                  type="button"
                  className={`marker marker--${tone}${selectedId === m.id ? " is-selected" : ""}`}
                  style={{ left: pct(m.seconds) }}
                  onClick={() => onSelect(m.id)}
                  aria-pressed={selectedId === m.id}
                  title={tooltip}
                >
                  <span className="marker__glyph" aria-hidden="true">
                    {glyph}
                  </span>
                  <span className="visually-hidden">{accessibleText}</span>
                </button>
              );
            })
          : null}
      </div>

      <div className="rail__track">
        <span className="rail__progress" style={{ width: pct(currentTime) }} aria-hidden="true" />
        <input
          type="range"
          className="rail__input"
          min={0}
          max={safeDuration || 1}
          step={0.05}
          value={Math.min(currentTime, safeDuration || 1)}
          disabled={safeDuration === 0}
          onChange={(e) => onScrub(Number(e.target.value))}
          aria-label="Master timeline position"
          aria-valuetext={`${timecode(currentTime, true)} of ${timecode(safeDuration, true)}`}
        />
      </div>

      <p className="rail__times">
        <b>{timecode(currentTime, true)}</b>
        <span>{timecode(safeDuration, true)}</span>
      </p>
    </div>
  );
}
