"use client";

import { useCallback, useId, useRef, useState } from "react";
import { bytes, timecode } from "../lib/format";

export type MediaSlot = {
  file: File;
  /** Object URL created once per file and revoked by the owner. */
  url: string;
};

export type MediaMeta = { duration: number; width: number; height: number };

type Props = {
  role: "V1" | "V2";
  title: string;
  hint: string;
  slot: MediaSlot | null;
  meta: MediaMeta | null;
  onSelect: (file: File | null) => void;
  onMeta: (meta: MediaMeta | null) => void;
  disabled?: boolean;
};

export function DropZone({ role, title, hint, slot, meta, onSelect, onMeta, disabled }: Props) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [metaFailed, setMetaFailed] = useState(false);

  const take = useCallback(
    (file: File | null | undefined) => {
      if (!file) return;
      setMetaFailed(false);
      onMeta(null);
      onSelect(file);
    },
    [onMeta, onSelect],
  );

  return (
    <div
      className={`drop${slot ? " is-filled" : ""}${dragging ? " is-dragging" : ""}`}
      onDragOver={(e) => {
        if (disabled) return;
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        if (disabled) return;
        e.preventDefault();
        setDragging(false);
        const file = Array.from(e.dataTransfer.files).find((f) => f.type.startsWith("video/"));
        take(file ?? e.dataTransfer.files[0]);
      }}
    >
      <div className="drop__head">
        <span className="drop__role">{role}</span>
        <span className="drop__title">{title}</span>
      </div>

      {slot ? (
        <div className="drop__body">
          <video
            className="drop__thumb"
            src={slot.url}
            muted
            playsInline
            preload="metadata"
            aria-hidden="true"
            onLoadedMetadata={(e) => {
              const el = e.currentTarget;
              const duration = Number.isFinite(el.duration) ? el.duration : 0;
              onMeta({ duration, width: el.videoWidth, height: el.videoHeight });
            }}
            onError={() => {
              setMetaFailed(true);
              onMeta(null);
            }}
          />
          <div className="drop__facts">
            <strong title={slot.file.name}>{slot.file.name}</strong>
            <ul>
              <li>{bytes(slot.file.size)}</li>
              {meta ? <li>{timecode(meta.duration, true)}</li> : null}
              {meta && meta.width ? (
                <li>
                  {meta.width}×{meta.height}
                </li>
              ) : null}
              {metaFailed ? <li className="is-warn">metadata unreadable — upload still works</li> : null}
            </ul>
          </div>
        </div>
      ) : (
        <div className="drop__body drop__body--empty">
          <p className="drop__hint">{hint}</p>
          <p className="drop__cta">Drag a file here, or choose one</p>
        </div>
      )}

      <div className="drop__actions">
        <label className="btn btn--ghost" htmlFor={inputId}>
          {slot ? "Replace" : "Choose file"}
        </label>
        {slot ? (
          <button
            type="button"
            className="btn btn--quiet"
            onClick={() => {
              onSelect(null);
              onMeta(null);
              if (inputRef.current) inputRef.current.value = "";
            }}
            disabled={disabled}
          >
            Clear
          </button>
        ) : null}
        <input
          ref={inputRef}
          id={inputId}
          className="visually-hidden"
          type="file"
          accept="video/*"
          disabled={disabled}
          onChange={(e) => take(e.target.files?.[0] ?? null)}
        />
      </div>
    </div>
  );
}
