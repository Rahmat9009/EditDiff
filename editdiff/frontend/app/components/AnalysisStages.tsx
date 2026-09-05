"use client";

import { useEffect, useState } from "react";

const STAGES = [
  "Reading revision notes",
  "Aligning the two exports",
  "Sampling audio and visual evidence",
  "Verifying requested intent",
  "Building the evidence ledger",
];

/**
 * Indeterminate staged progress. The backend reports no progress events, so
 * stages advance on a timer, hold on the last one, and are never labelled as
 * "complete" — only the finished report proves completion.
 */
export function AnalysisStages() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => {
      setActive((i) => Math.min(i + 1, STAGES.length - 1));
    }, 1400);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="stages" role="status" aria-live="polite">
      <div className="stages__bar" aria-hidden="true">
        <span />
      </div>
      <p className="stages__now">{STAGES[active]}…</p>
      <ol>
        {STAGES.map((stage, i) => (
          <li key={stage} className={i < active ? "is-past" : i === active ? "is-active" : ""}>
            <span className="stages__dot" aria-hidden="true" />
            {stage}
          </li>
        ))}
      </ol>
      <p className="stages__note">
        Stage timings are indicative. The audit finishes when the verifier returns its ledger.
      </p>
    </div>
  );
}
