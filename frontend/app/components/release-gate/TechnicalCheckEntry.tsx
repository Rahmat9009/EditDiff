"use client";

import { percent, timecode } from "../../lib/format";
import { technicalCheckTimestamp, type TechnicalCheck } from "../../lib/releaseGate";
import { MetricTable } from "../MetricTable";
import { SeverityTag, TechnicalStatusBadge } from "./DispositionBadge";

type Props = {
  check: TechnicalCheck;
  index: number;
  selected: boolean;
  onSelect: () => void;
};

export function TechnicalCheckEntry({ check, index, selected, onSelect }: Props) {
  const tone = check.status.toLowerCase().replaceAll("_", "-");
  const seconds = technicalCheckTimestamp(check);
  const { evidence } = check;
  const hasDetail =
    !!evidence.metrics?.length || !!evidence.reason_codes?.length || !!evidence.methods?.length;

  return (
    <article
      className={`entry entry--technical entry--tech-${tone}${selected ? " is-selected" : ""}`}
      aria-current={selected ? "true" : undefined}
    >
      <h4 className="entry__title">
        <button type="button" className="entry__head" onClick={onSelect} aria-expanded={selected}>
          <span className="entry__index">{String(index + 1).padStart(2, "0")}</span>
          <TechnicalStatusBadge status={check.status} />
          <span className="entry__request">
            <span className="entry__text">{check.label}</span>
            <span className="entry__meta">
              {seconds != null ? `${timecode(seconds)} · ` : ""}
              {check.severity === "BLOCKING" ? "blocking check" : "advisory check"} ·{" "}
              {selected ? "showing detail" : seconds != null ? "jump to moment" : "open detail"}
            </span>
          </span>
          <span className="entry__confidence entry__confidence--level">
            <SeverityTag severity={check.severity} />
          </span>
        </button>
      </h4>

      <div className="entry__body">
        <p className="entry__reason">{check.explanation}</p>

        <p className="entry__evidence-line">
          <span className="entry__tag">Check</span>
          <span className="entry__check-id">{check.id}</span>
          <span className="entry__tag">Confidence</span>
          <span>{percent(check.confidence)}</span>
        </p>

        {check.status === "NOT_APPLICABLE" ? (
          <p className="entry__stance">
            Not applicable to this pair of exports. No conclusion is recorded either way.
          </p>
        ) : check.status === "REVIEW" ? (
          <p className="entry__stance">
            Held for review: the measurement did not settle this check in either direction.
          </p>
        ) : null}

        {selected && hasDetail ? (
          <details className="disclosure" open>
            <summary>Inspect check details</summary>
            {evidence.methods?.length ? (
              <p className="disclosure__note">
                Methods: {evidence.methods.map((m) => m.replaceAll("_", " ")).join(", ")}
              </p>
            ) : null}
            {evidence.reason_codes?.length ? (
              <p className="disclosure__note">
                Reason codes: {evidence.reason_codes.map((r) => r.replaceAll("_", " ")).join(", ")}
              </p>
            ) : null}
            {evidence.thresholds && Object.keys(evidence.thresholds).length ? (
              <p className="disclosure__note">
                Thresholds:{" "}
                {Object.entries(evidence.thresholds)
                  .map(([name, value]) => `${name.replaceAll("_", " ")}: ${value}`)
                  .join("; ")}
              </p>
            ) : null}
            {evidence.metrics?.length ? <MetricTable metrics={evidence.metrics} /> : null}
          </details>
        ) : null}
      </div>
    </article>
  );
}
