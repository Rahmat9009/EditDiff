"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { timecode } from "../lib/format";
import { TimelineRail, type ViewerMarker } from "./TimelineRail";

export type ComparisonViewerCoreProps = {
  v1Url: string | null;
  v2Url: string | null;
  v1Label?: string;
  v2Label?: string;
  v1AudioLabel?: string;
  v2AudioLabel?: string;
  markers: ViewerMarker[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  seek: { aTime: number; bTime: number; nonce: number } | null;
  caption?: ReactNode;
  emptyMessage?: string;
  timelineSource?: "a" | "b";
};

type Mode = "split" | "wipe";
type AudioSource = "v1" | "v2";

const SYNC_TOLERANCE = 0.18;

export function ComparisonViewerCore({
  v1Url,
  v2Url,
  v1Label = "V1 · BEFORE",
  v2Label = "V2 · AFTER",
  v1AudioLabel = "Hear V1",
  v2AudioLabel = "Hear V2",
  markers,
  selectedId,
  onSelect,
  seek,
  caption,
  emptyMessage = "Source files are no longer in memory. Re-select both exports to use the comparison view.",
  timelineSource = "a",
}: ComparisonViewerCoreProps) {
  const aRef = useRef<HTMLVideoElement>(null);
  const bRef = useRef<HTMLVideoElement>(null);
  const rafRef = useRef<number | null>(null);

  const [mode, setMode] = useState<Mode>("split");
  const [audioSource, setAudioSource] = useState<AudioSource>("v2");
  const [wipe, setWipe] = useState(50);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [durationA, setDurationA] = useState(0);
  const [durationB, setDurationB] = useState(0);
  const [mediaError, setMediaError] = useState(false);

  // Offset lock between player B and player A:
  // final (B) = preFinal (A) + offsetRef.current  <=>  preFinal (A) = final (B) - offsetRef.current
  const offsetRef = useRef(0);

  const sync = useCallback(() => {
    const a = aRef.current;
    const b = bRef.current;
    if (!a || !b) return;

    const offset = offsetRef.current;
    const expectedB = a.currentTime + offset;

    if (!a.paused && Number.isFinite(b.duration) && expectedB >= b.duration) {
      a.pause();
      b.pause();
      setPlaying(false);
    }
    if (!a.paused && Number.isFinite(a.duration) && a.currentTime >= a.duration) {
      a.pause();
      b.pause();
      setPlaying(false);
    }

    if (Math.abs(b.currentTime - expectedB) > SYNC_TOLERANCE) {
      b.currentTime = Math.max(0, Math.min(expectedB, b.duration || expectedB));
    }

    if (timelineSource === "b") {
      setCurrentTime(b.currentTime);
    } else {
      setCurrentTime(a.currentTime);
    }
  }, [timelineSource]);

  useEffect(() => {
    if (!playing) {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
      return;
    }
    const tick = () => {
      sync();
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    };
  }, [playing, sync]);

  const seekBoth = useCallback(
    (aTarget: number, bTarget: number) => {
      const a = aRef.current;
      const b = bRef.current;
      if (!a) return;

      const safeA = Math.max(0, Math.min(aTarget, a.duration || aTarget));
      a.currentTime = safeA;

      if (b) {
        const safeB = Math.max(0, Math.min(bTarget, b.duration || bTarget));
        b.currentTime = safeB;
        offsetRef.current = safeB - safeA;
        setCurrentTime(timelineSource === "b" ? safeB : safeA);
      } else {
        offsetRef.current = 0;
        setCurrentTime(safeA);
      }
    },
    [timelineSource],
  );

  const seekNonce = seek?.nonce;
  const aTime = seek?.aTime;
  const bTime = seek?.bTime;
  useEffect(() => {
    if (seekNonce === undefined || aTime === undefined || bTime === undefined) return;
    seekBoth(aTime, bTime);
  }, [seekNonce, aTime, bTime, seekBoth]);

  const pause = useCallback(() => {
    aRef.current?.pause();
    bRef.current?.pause();
    setPlaying(false);
  }, []);

  const play = useCallback(async () => {
    const a = aRef.current;
    const b = bRef.current;
    if (!a || !b) return;

    const offset = offsetRef.current;
    if (timelineSource === "b") {
      if (b.currentTime >= (b.duration || 0) - 0.05 || (b.currentTime - offset) >= (a.duration || 0) - 0.05) {
        seekBoth(Math.max(0, -offset), 0);
        offsetRef.current = offset;
      }
      a.currentTime = Math.max(0, Math.min(b.currentTime - offset, a.duration || (b.currentTime - offset)));
    } else {
      if (a.currentTime >= (a.duration || 0) - 0.05 || (a.currentTime + offset) >= (b.duration || 0) - 0.05) {
        seekBoth(0, Math.max(0, offset));
      }
      b.currentTime = Math.max(0, Math.min(a.currentTime + offset, b.duration || (a.currentTime + offset)));
    }

    try {
      await Promise.all([a.play(), b.play()]);
      setPlaying(true);
    } catch {
      pause();
      setMediaError(true);
    }
  }, [pause, seekBoth, timelineSource]);

  const toggle = useCallback(() => {
    if (playing) pause();
    else void play();
  }, [pause, play, playing]);

  const step = useCallback(
    (delta: number) => {
      pause();
      const offset = offsetRef.current;
      if (timelineSource === "b") {
        const b = bRef.current;
        const curB = b ? b.currentTime : currentTime;
        const targetB = curB + delta;
        const targetA = targetB - offset;
        seekBoth(targetA, targetB);
        offsetRef.current = offset;
      } else {
        const a = aRef.current;
        const curA = a ? a.currentTime : currentTime;
        seekBoth(curA + delta, curA + delta + offset);
      }
    },
    [currentTime, pause, seekBoth, timelineSource],
  );

  if (!v1Url || !v2Url) {
    return (
      <section className="viewer viewer--empty">
        <p>{emptyMessage}</p>
      </section>
    );
  }

  return (
    <section className="viewer" aria-label="Synchronised comparison">
      <div className={`viewer__stage viewer__stage--${mode}`}>
        <figure className="viewer__pane viewer__pane--a">
          <video
            ref={aRef}
            src={v1Url}
            playsInline
            preload="metadata"
            muted={audioSource !== "v1"}
            onLoadedMetadata={(e) => setDurationA(e.currentTarget.duration || 0)}
            onTimeUpdate={sync}
            onEnded={pause}
            onError={() => setMediaError(true)}
          />
          <figcaption>{v1Label}</figcaption>
        </figure>

        <figure
          className="viewer__pane viewer__pane--b"
          style={mode === "wipe" ? { clipPath: `inset(0 0 0 ${wipe}%)` } : undefined}
        >
          <video
            ref={bRef}
            src={v2Url}
            playsInline
            preload="metadata"
            muted={audioSource !== "v2"}
            onLoadedMetadata={(e) => setDurationB(e.currentTarget.duration || 0)}
            onEnded={pause}
            onError={() => setMediaError(true)}
          />
          <figcaption>{v2Label}</figcaption>
        </figure>

        {mode === "wipe" ? (
          <>
            <span className="viewer__wipe-line" style={{ left: `${wipe}%` }} aria-hidden="true" />
            <input
              type="range"
              className="viewer__wipe-input"
              min={0}
              max={100}
              step={0.5}
              value={wipe}
              onChange={(e) => setWipe(Number(e.target.value))}
              aria-label="Before and after wipe position"
              aria-valuetext={`${Math.round(wipe)} percent revised export`}
            />
          </>
        ) : null}

        {caption ? <div className="viewer__caption">{caption}</div> : null}
      </div>

      <div className="viewer__transport">
        <button type="button" className="btn btn--play" onClick={toggle}>
          {playing ? "Pause" : "Play both"}
        </button>
        <button
          type="button"
          className="btn btn--quiet"
          onClick={() => step(-1)}
          aria-label="Back one second"
        >
          −1s
        </button>
        <button
          type="button"
          className="btn btn--quiet"
          onClick={() => step(1)}
          aria-label="Forward one second"
        >
          +1s
        </button>

        <div className="viewer__toggles">
          <fieldset className="segmented">
            <legend className="visually-hidden">Comparison mode</legend>
            {(["split", "wipe"] as Mode[]).map((m) => (
              <label key={m} className={mode === m ? "is-active" : ""}>
                <input
                  type="radio"
                  name="viewer-mode"
                  value={m}
                  checked={mode === m}
                  onChange={() => setMode(m)}
                />
                {m === "split" ? "Split" : "Wipe"}
              </label>
            ))}
          </fieldset>
          <fieldset className="segmented">
            <legend className="visually-hidden">Audio source</legend>
            {(["v1", "v2"] as AudioSource[]).map((s) => (
              <label key={s} className={audioSource === s ? "is-active" : ""}>
                <input
                  type="radio"
                  name="viewer-audio"
                  value={s}
                  checked={audioSource === s}
                  onChange={() => setAudioSource(s)}
                />
                {s === "v1" ? v1AudioLabel : v2AudioLabel}
              </label>
            ))}
          </fieldset>
        </div>
      </div>

      <TimelineRail
        duration={timelineSource === "b" ? (durationB || durationA) : (durationA || durationB)}
        currentTime={currentTime}
        markers={markers}
        selectedId={selectedId}
        onScrub={(t) => {
          pause();
          if (timelineSource === "b") {
            const offset = offsetRef.current;
            seekBoth(t - offset, t);
            offsetRef.current = offset;
          } else {
            seekBoth(t, t + offsetRef.current);
          }
        }}
        onSelect={onSelect}
      />

      {mediaError ? (
        <p className="viewer__warn" role="status">
          This browser could not decode one of the exports. The analysis report and extracted evidence are unaffected.
        </p>
      ) : null}
    </section>
  );
}
