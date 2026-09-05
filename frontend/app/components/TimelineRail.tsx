"use client";

import { timecode, VERDICT_GLYPH } from "../lib/format";
import type { Verdict } from "../lib/types";

export type Marker = {
  id: string;
  seconds: number;
  verdict: Verdict;
  label: string;
  index: number;
};

type Props = {
  duration: number;
  currentTime: number;
  markers: Marker[];
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
          ? markers.map((m) => (
              <button
                key={m.id}
                type="button"
                className={`marker marker--${m.verdict.toLowerCase()}${
                  selectedId === m.id ? " is-selected" : ""
                }`}
                style={{ left: pct(m.seconds) }}
                onClick={() => onSelect(m.id)}
                aria-pressed={selectedId === m.id}
                title={`${timecode(m.seconds)} · ${m.verdict} · ${m.label}`}
              >
                <span className="marker__glyph" aria-hidden="true">
                  {VERDICT_GLYPH[m.verdict]}
                </span>
                <span className="visually-hidden">
                  Revision {m.index} at {timecode(m.seconds)}, {m.verdict}: {m.label}
                </span>
              </button>
            ))
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
