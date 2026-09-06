import type { ChangeKind } from "../lib/types";

export const KIND_GLYPH: Record<ChangeKind, string> = {
  VISUAL: "◈",
  TIMING: "⧖",
  AUDIO: "∿",
  TEXT: "T",
  REVIEW: "?",
};

export function ChangeKindBadge({
  kind,
  size = "md",
}: {
  kind: ChangeKind;
  size?: "sm" | "md";
}) {
  const kindClass = kind.toLowerCase();
  return (
    <span className={`kind-badge kind-badge--${kindClass} kind-badge--${size}`}>
      <span className="kind-badge__glyph" aria-hidden="true">
        {KIND_GLYPH[kind] ?? "•"}
      </span>
      {kind}
    </span>
  );
}
