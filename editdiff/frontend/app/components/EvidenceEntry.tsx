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
            {evidence.window_start_seconds != null && evidence.window_end_seconds != null ? (
              <p className="disclosure__note">
                Evidence window: {timecode(evidence.window_start_seconds, true)}–{timecode(evidence.window_end_seconds, true)}
              </p>
            ) : null}
            {evidence.semantic_status && evidence.semantic_status !== "not_requested" ? (
              <p className="disclosure__note">
                {evidence.semantic_status === "available"
                  ? "Semantic inspection available; combined with measured evidence."
                  : "Semantic inspection unavailable; this verdict uses measured evidence only."}
              </p>
            ) : null}
            {evidence.signal_agreement === "disagreement" ? (
              <p className="disclosure__note">The measured and semantic signals disagree. Human review is needed.</p>
            ) : null}
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

            {evidence.after_observation ? (
              <div className="semantic">
                <p className="semantic__head">Observed revision</p>
                {evidence.before_observation ? <p className="semantic__body">Before: {evidence.before_observation}</p> : null}
                <p className="semantic__body">After: {evidence.after_observation}</p>
              </div>
            ) : null}
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
              <summary>Inspect verification details</summary>
              {evidence.methods?.length ? <p className="disclosure__note">Methods: {evidence.methods.map((m) => m.replaceAll("_", " ")).join(", ")}</p> : null}
              {evidence.reason_codes?.length ? <p className="disclosure__note">Reason: {evidence.reason_codes.map((r) => r.replaceAll("_", " ")).join(", ")}</p> : null}
              {evidence.thresholds && Object.keys(evidence.thresholds).length ? (
                <p className="disclosure__note">Thresholds: {Object.entries(evidence.thresholds).map(([name, value]) => `${name.replaceAll("_", " ")}: ${value}`).join("; ")}</p>
              ) : null}
              <MetricTable metrics={evidence.metrics} />
              <p className="disclosure__note">{VERDICT_MEANING[verdict]}</p>
            </details>
          </>
        ) : null}
      </div>
    </article>
  );
}
