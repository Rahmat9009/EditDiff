"use client";

import { timecode } from "../../lib/format";
import { technicalCheckDetail, type TechnicalCheck } from "../../lib/releaseGate";
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
  const detail = technicalCheckDetail(check);
  const timed = check.timestamp_seconds != null;

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
            <span className="entry__text">{check.name}</span>
            <span className="entry__meta">
              {timed ? `${timecode(check.timestamp_seconds)} · ` : ""}
              {check.severity === "BLOCKING" ? "blocking check" : "advisory check"} ·{" "}
              {selected ? "showing detail" : timed ? "jump to moment" : "open detail"}
            </span>
          </span>
          <span className="entry__confidence entry__confidence--level">
            <SeverityTag severity={check.severity} />
          </span>
        </button>
      </h4>

      <div className="entry__body">
        {detail ? <p className="entry__reason">{detail}</p> : null}

        {check.expected || check.observed ? (
          <p className="entry__evidence-line">
            {check.expected ? (
              <>
                <span className="entry__tag">Expected</span>
                <span>{check.expected}</span>
              </>
            ) : null}
            {check.observed ? (
              <>
                <span className="entry__tag">Observed</span>
                <span>{check.observed}</span>
              </>
            ) : null}
          </p>
        ) : null}

        {check.status === "NOT_APPLICABLE" ? (
          <p className="entry__stance">
            Not applicable to this pair of exports. No conclusion is recorded either way.
          </p>
        ) : check.status === "REVIEW" ? (
          <p className="entry__stance">
            Held for review: the measurement did not settle this check in either direction.
          </p>
        ) : null}

        {selected && (check.metrics?.length || check.reason_codes?.length) ? (
          <details className="disclosure" open>
            <summary>Inspect check details</summary>
            {check.reason_codes?.length ? (
              <p className="disclosure__note">
                Reason codes: {check.reason_codes.map((r) => r.replaceAll("_", " ")).join(", ")}
              </p>
            ) : null}
            {check.metrics?.length ? <MetricTable metrics={check.metrics} /> : null}
          </details>
        ) : null}
      </div>
    </article>
  );
}
