import { VERDICT_GLYPH } from "../lib/format";
import type { Verdict } from "../lib/types";

export function VerdictBadge({ verdict, size = "md" }: { verdict: Verdict; size?: "sm" | "md" }) {
  return (
    <span className={`verdict verdict--${verdict.toLowerCase()} verdict--${size}`}>
      <span className="verdict__glyph" aria-hidden="true">
        {VERDICT_GLYPH[verdict] ?? "•"}
      </span>
      {verdict}
    </span>
  );
}
