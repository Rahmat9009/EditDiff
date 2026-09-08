"use client";

import { useEffect, useState } from "react";
import { DECISION_GLYPH, DECISION_LABEL, type ReleaseGateResult } from "../../lib/releaseGate";

type Props = { busy: boolean; result: ReleaseGateResult | null };

export function ReleaseGateStatusPanel({ busy, result }: Props) {
  return (
    <aside className="panel status status--gate" aria-labelledby="gate-status-heading">
      <div className="panel__head">
        <span className="panel__index">02</span>
        <h2 id="gate-status-heading">Release readiness</h2>
      </div>

      {busy ? (
        <GateStages />
      ) : !result ? (
        <div className="status__empty">
          <div className="status__target" aria-hidden="true">
            <span />
            <span />
          </div>
          <p className="status__empty-lead">No gate run yet.</p>
          <p className="status__empty-note">
            The gate checks the requested revisions, everything that changed without being
            requested, and the technical state of the candidate — then states one decision with the
            reasons behind it.
          </p>
        </div>
      ) : (
        <GateSummary result={result} />
      )}
    </aside>
  );
}

const STAGES = [
  "Aligning baseline and candidate",
  "Verifying requested revisions",
  "Detecting unrequested changes",
  "Associating changes with requests",
  "Running technical QA",
  "Reaching a release decision",
];

function GateStages() {
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
        Stage timings are indicative. The gate finishes when the API returns its decision.
      </p>
    </div>
  );
}

function GateSummary({ result }: { result: ReleaseGateResult }) {
  const { summary, decision } = result;
  const tone = decision.toLowerCase().replaceAll("_", "-");

  /* backend/app/release_gate.py decide_release(): only a failed requested
     revision or a failed BLOCKING technical check blocks a release. Unexpected
     changes, ambiguous associations and review-status checks hold it for a
     human instead. Follow the decision the backend actually made rather than
     re-deriving one here. */
  const blocking = summary.requested_failed + summary.technical_failed;
  const held =
    summary.requested_review +
    summary.unexpected_changes +
    summary.change_association_review +
    summary.technical_review;

  return (
    <div className={`gate-score gate-score--${tone}`}>
      <p className="gate-score__decision">
        <span className="gate-score__glyph" aria-hidden="true">
          {DECISION_GLYPH[decision]}
        </span>
        {DECISION_LABEL[decision]}
      </p>

      <ul className="gate-score__rows">
        <li>
          <span>Requested revisions verified</span>
          <b>
            {summary.requested_passed}/{summary.requested_total}
          </b>
        </li>
        <li>
          <span>Unexpected changes</span>
          <b>{summary.unexpected_changes}</b>
        </li>
        <li>
          <span>Changes accounted for</span>
          <b>{summary.accounted_changes}</b>
        </li>
        <li>
          <span>Technical checks failing</span>
          <b>{summary.technical_failed}</b>
        </li>
      </ul>

      <p className="score__call">
        {decision === "BLOCKED"
          ? `${blocking} finding${blocking === 1 ? "" : "s"} contradict${
              blocking === 1 ? "s" : ""
            } this release.${
              held > 0 ? ` ${held} more need${held === 1 ? "s" : ""} a human decision.` : ""
            }`
          : decision === "NEEDS_REVIEW"
            ? `${held} finding${held === 1 ? "" : "s"} need${
                held === 1 ? "s" : ""
              } a human decision before publishing — including anything that changed outside the notes.`
            : "No unresolved changes detected above current thresholds."}
      </p>

      <p className="score__id">
        Report <b>{result.report_id.toUpperCase()}</b>
      </p>
    </div>
  );
}
