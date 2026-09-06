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
}: ComparisonViewerCoreProps) {
  const aRef = useRef<HTMLVideoElement>(null);
  const bRef = useRef<HTMLVideoElement>(null);
  const rafRef = useRef<number | null>(null);

  const [mode, setMode] = useState<Mode>("split");
  const [audioSource, setAudioSource] = useState<AudioSource>("v2");
  const [wipe, setWipe] = useState(50);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [mediaError, setMediaError] = useState(false);

  // Offset lock between player B and player A: b.currentTime = a.currentTime + offsetRef.current
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

    if (Math.abs(b.currentTime - expectedB) > SYNC_TOLERANCE) {
      b.currentTime = Math.max(0, Math.min(expectedB, b.duration || expectedB));
    }
    setCurrentTime(a.currentTime);
  }, []);

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

  const seekBoth = useCallback((aTarget: number, bTarget: number) => {
    const a = aRef.current;
    const b = bRef.current;
    if (!a) return;

    const safeA = Math.max(0, Math.min(aTarget, a.duration || aTarget));
    a.currentTime = safeA;

    if (b) {
      const safeB = Math.max(0, Math.min(bTarget, b.duration || bTarget));
      b.currentTime = safeB;
      offsetRef.current = safeB - safeA;
    } else {
      offsetRef.current = 0;
    }
    setCurrentTime(safeA);
  }, []);

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
    if (a.currentTime >= a.duration - 0.05 || (a.currentTime + offset) >= b.duration - 0.05) {
      seekBoth(0, Math.max(0, offset));
    }
    b.currentTime = Math.max(0, Math.min(a.currentTime + offset, b.duration || (a.currentTime + offset)));

    try {
      await Promise.all([a.play(), b.play()]);
      setPlaying(true);
    } catch {
      pause();
      setMediaError(true);
    }
  }, [pause, seekBoth]);

  const toggle = useCallback(() => {
    if (playing) pause();
    else void play();
  }, [pause, play, playing]);

  const step = useCallback(
    (delta: number) => {
      pause();
      const a = aRef.current;
      const curA = a ? a.currentTime : currentTime;
      seekBoth(curA + delta, curA + delta + offsetRef.current);
    },
    [currentTime, pause, seekBoth],
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
            onLoadedMetadata={(e) => setDuration(e.currentTarget.duration || 0)}
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
        duration={duration}
        currentTime={currentTime}
        markers={markers}
        selectedId={selectedId}
        onScrub={(t) => {
          pause();
          seekBoth(t, t + offsetRef.current);
        }}
        onSelect={onSelect}
      />

      {mediaError ? (
        <p className="viewer__warn" role="status">
          This browser could not decode one of the exports. Verdicts and evidence frames are unaffected.
        </p>
      ) : null}
    </section>
  );
}
