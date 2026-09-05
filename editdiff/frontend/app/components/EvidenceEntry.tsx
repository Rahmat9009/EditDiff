"use client";

import { kindLabel, percent, timecode, VERDICT_MEANING } from "../lib/format";
import { semanticOf, type Result } from "../lib/types";
import { EvidenceFrame } from "./EvidenceFrame";
import { MetricTable } from "./MetricTable";
import { VerdictBadge } from "./VerdictBadge";

type Props = {
  result: Result;
  index: number;
  selected: boolean;
  onSelect: () => void;
};

export function EvidenceEntry({ result, index, selected, onSelect }: Props) {
  const { request, evidence, verdict, confidence } = result;
  const semantic = semanticOf(evidence);
  const seconds = evidence.timestamp_seconds ?? request.timestamp_seconds ?? null;

  return (
    <article
      className={`entry entry--${verdict.toLowerCase()}${selected ? " is-selected" : ""}`}
      aria-current={selected ? "true" : undefined}
    >
      <h3 className="entry__title">
        <button type="button" className="entry__head" onClick={onSelect} aria-expanded={selected}>
          <span className="entry__index">{String(index + 1).padStart(2, "0")}</span>
          <VerdictBadge verdict={verdict} />
          <span className="entry__request">
            <span className="entry__text">{request.raw_text}</span>
            <span className="entry__meta">
              {timecode(seconds)} · {kindLabel(request.kind)} check ·{" "}
              {selected ? "showing evidence" : "jump to proof"}
            </span>
          </span>
          <span className="entry__confidence">
            <b>{percent(confidence)}</b>
            <span>confidence</span>
          </span>
        </button>
      </h3>

      <div className="entry__body">
        <p className="entry__reason">{evidence.explanation}</p>

        {selected ? (
          <>
            <div className="entry__frames">
              <EvidenceFrame
                path={evidence.v1_frame_path}
                label={`V1 · BEFORE · ${timecode(seconds)}`}
                alt={`Previous export at ${timecode(seconds)} for: ${request.raw_text}`}
              />
              <EvidenceFrame
                path={evidence.v2_frame_path}
                label={`V2 · AFTER · ${timecode(seconds)}`}
                alt={`Revised export at ${timecode(seconds)} for: ${request.raw_text}`}
              />
            </div>

            {semantic ? (
              <div className="semantic">
                <p className="semantic__head">
                  Semantic check
                  {semantic.model ? <span>{String(semantic.model)}</span> : null}
                  {typeof semantic.confidence === "number" ? (
                    <span>{percent(semantic.confidence)}</span>
                  ) : null}
                </p>
                <p className="semantic__body">
                  {String(semantic.rationale ?? semantic.explanation ?? semantic.verdict ?? "")}
                </p>
                {semantic.expected || semantic.observed ? (
                  <dl className="semantic__pairs">
                    {semantic.expected ? (
                      <div>
                        <dt>Requested</dt>
                        <dd>{String(semantic.expected)}</dd>
                      </div>
                    ) : null}
                    {semantic.observed ? (
                      <div>
                        <dt>Observed in V2</dt>
                        <dd>{String(semantic.observed)}</dd>
                      </div>
                    ) : null}
                  </dl>
                ) : null}
              </div>
            ) : null}

            <details className="disclosure">
              <summary>Inspect deterministic signals</summary>
              <MetricTable metrics={evidence.metrics} />
              <p className="disclosure__note">{VERDICT_MEANING[verdict]}</p>
            </details>
          </>
        ) : null}
      </div>
    </article>
  );
}
