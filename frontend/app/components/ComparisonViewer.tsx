"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { timecode } from "../lib/format";
import type { Verdict } from "../lib/types";
import { TimelineRail, type Marker } from "./TimelineRail";
import { VerdictBadge } from "./VerdictBadge";

type Props = {
  v1Url: string | null;
  v2Url: string | null;
  markers: Marker[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** Seek requests from the ledger; the nonce re-triggers an identical time. */
  seek: { time: number; nonce: number } | null;
  caption: { label: string; verdict: Verdict; seconds: number | null } | null;
};

type Mode = "split" | "wipe";
type AudioSource = "v1" | "v2";

const SYNC_TOLERANCE = 0.18;

export function ComparisonViewer({
  v1Url,
  v2Url,
  markers,
  selectedId,
  onSelect,
  seek,
  caption,
}: Props) {
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

  /** Keep V2 locked to the V1 master clock. */
  const sync = useCallback(() => {
    const a = aRef.current;
    const b = bRef.current;
    if (!a || !b) return;
    if (!a.paused && Number.isFinite(b.duration) && a.currentTime >= b.duration) {
      a.pause();
      b.pause();
      a.currentTime = b.duration;
      setPlaying(false);
    }
    if (Math.abs(b.currentTime - a.currentTime) > SYNC_TOLERANCE) {
      b.currentTime = Math.min(a.currentTime, b.duration || a.currentTime);
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

  const seekTo = useCallback((time: number) => {
    const a = aRef.current;
    const b = bRef.current;
    if (!a) return;
    const target = Math.max(0, Math.min(time, a.duration || time));
    a.currentTime = target;
    if (b) b.currentTime = Math.max(0, Math.min(target, b.duration || target));
    setCurrentTime(target);
  }, []);

  const seekNonce = seek?.nonce;
  const seekTime = seek?.time;
  useEffect(() => {
    if (seekNonce === undefined || seekTime === undefined) return;
    seekTo(seekTime);
  }, [seekNonce, seekTime, seekTo]);

  const pause = useCallback(() => {
    aRef.current?.pause();
    bRef.current?.pause();
    setPlaying(false);
  }, []);

  const play = useCallback(async () => {
    const a = aRef.current;
    const b = bRef.current;
    if (!a || !b) return;
    if (a.currentTime >= Math.min(a.duration, b.duration) - 0.05) seekTo(0);
    b.currentTime = a.currentTime;
    try {
      await Promise.all([a.play(), b.play()]);
      setPlaying(true);
    } catch {
      pause();
      setMediaError(true);
    }
  }, [pause, seekTo]);

  const toggle = useCallback(() => {
    if (playing) pause();
    else void play();
  }, [pause, play, playing]);

  const step = useCallback(
    (delta: number) => {
      pause();
      seekTo(currentTime + delta);
    },
    [currentTime, pause, seekTo],
  );

  if (!v1Url || !v2Url) {
    return (
      <section className="viewer viewer--empty">
        <p>Source files are no longer in memory. Re-select both exports to use the comparison view.</p>
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
          <figcaption>V1 · BEFORE</figcaption>
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
          <figcaption>V2 · AFTER</figcaption>
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

        {caption ? (
          <p className="viewer__caption">
            <VerdictBadge verdict={caption.verdict} size="sm" />
            <span className="viewer__caption-text">{caption.label}</span>
            <span className="viewer__caption-ts">{timecode(caption.seconds)}</span>
          </p>
        ) : null}
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
                {s === "v1" ? "Hear V1" : "Hear V2"}
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
          seekTo(t);
        }}
        onSelect={onSelect}
      />

      {mediaError ? (
        <p className="viewer__warn" role="status">
          This browser could not decode one of the exports. The analysis report and extracted evidence are
          unaffected.
        </p>
      ) : null}
    </section>
  );
}
