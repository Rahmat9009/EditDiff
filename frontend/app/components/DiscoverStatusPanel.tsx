"use client";

import { useEffect, useState } from "react";
import type { ChangeKind, DiscoverReport } from "../lib/types";
import { ChangeKindBadge } from "./ChangeKindBadge";

type Props = {
  busy: boolean;
  report: DiscoverReport | null;
};

const DISCOVER_STAGES = [
  "Aligning versions",
  "Finding changes",
  "Verifying evidence",
  "Building ledger",
];

export function DiscoverStatusPanel({ busy, report }: Props) {
  return (
    <aside className="panel status status--discover" aria-labelledby="discover-status-heading">
      <div className="panel__head">
        <span className="panel__index">02</span>
        <h2 id="discover-status-heading">Change summary</h2>
      </div>

      {busy ? (
        <DiscoverStages />
      ) : !report ? (
        <div className="status__empty">
          <div className="status__target" aria-hidden="true">
            <span />
            <span />
          </div>
          <p className="status__empty-lead">No changes discovered yet.</p>
          <p className="status__empty-note">
            Select the pre-final and final exports to discover visual replacements, timing cuts,
            and audio changes with auditable evidence.
          </p>
        </div>
      ) : (
        <DiscoverScoreBody report={report} />
      )}
    </aside>
  );
}

function DiscoverStages() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => {
      setActive((i) => Math.min(i + 1, DISCOVER_STAGES.length - 1));
    }, 1500);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="stages" role="status" aria-live="polite">
      <div className="stages__bar" aria-hidden="true">
        <span />
      </div>
      <p className="stages__now">{DISCOVER_STAGES[active]}…</p>
      <ol>
        {DISCOVER_STAGES.map((stage, i) => (
          <li key={stage} className={i < active ? "is-past" : i === active ? "is-active" : ""}>
            <span className="stages__dot" aria-hidden="true" />
            {stage}
          </li>
        ))}
      </ol>
      <p className="stages__note">
        Stage timings are indicative. Discover completes once bounded sequence alignment and frame extraction finish.
      </p>
    </div>
  );
}

function DiscoverScoreBody({ report }: { report: DiscoverReport }) {
  const { summary } = report;
  const total = summary.total_changes;

  const kinds: { kind: ChangeKind; count: number }[] = [
    { kind: "VISUAL", count: summary.visual },
    { kind: "TIMING", count: summary.timing },
    { kind: "AUDIO", count: summary.audio },
    ...(summary.text > 0 ? [{ kind: "TEXT" as ChangeKind, count: summary.text }] : []),
    { kind: "REVIEW", count: summary.review },
  ];

  return (
    <div className="score score--discover">
      <p className="score__figure">
        <strong>{total}</strong>
        <span>
          meaningful change{total === 1 ? "" : "s"}
          <br />
          discovered between exports
        </span>
      </p>

      {total > 0 ? (
        <div
          className="score__ratio"
          role="img"
          aria-label={`${summary.visual} visual, ${summary.timing} timing, ${summary.audio} audio, ${summary.review} review`}
        >
          {kinds.map(({ kind, count }) =>
            count > 0 ? (
              <span
                key={kind}
                className={`score__seg score__seg--${kind.toLowerCase()}`}
                style={{ flexGrow: count / total }}
              />
            ) : null,
          )}
        </div>
      ) : null}

      <ul className="score__counts score__counts--discover">
        {kinds.map(({ kind, count }) => (
          <li key={kind}>
            <b>{count}</b>
            <ChangeKindBadge kind={kind} size="sm" />
          </li>
        ))}
      </ul>

      {total === 0 ? (
        <p className="score__call score__call--pass">
          No meaningful changes detected above current evidence thresholds. Sub-sample edits and subtle typography changes may require manual review.
        </p>
      ) : summary.review > 0 ? (
        <p className="score__call">
          {summary.review} item{summary.review === 1 ? "" : "s"} flagged for review where automatic confidence was bounded.
        </p>
      ) : (
        <p className="score__call score__call--pass">
          All detected changes are corroborated by deterministic visual, timing, or audio evidence.
        </p>
      )}

      <p className="score__id">
        Report <b>{report.report_id.toUpperCase()}</b>
      </p>
    </div>
  );
}
