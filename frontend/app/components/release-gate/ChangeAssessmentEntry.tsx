"use client";

import { timecode } from "../../lib/format";
import type { ReleaseChangeAssessment } from "../../lib/releaseGate";
import { ChangeKindBadge } from "../ChangeKindBadge";
import { EvidenceFrame } from "../EvidenceFrame";
import { MetricTable } from "../MetricTable";
import { DispositionBadge } from "./DispositionBadge";

type Props = {
  assessment: ReleaseChangeAssessment;
  index: number;
  selected: boolean;
  /** Raw text of each requested revision this change was matched to. */
  matchedRevisionTexts: string[];
  onSelect: () => void;
};

export function ChangeAssessmentEntry({
  assessment,
  index,
  selected,
  matchedRevisionTexts,
  onSelect,
}: Props) {
  const { change, disposition, explanation } = assessment;
  const { kind, title, description, evidence } = change;
  const preTs = evidence.pre_final_timestamp_seconds;
  const finalTs = evidence.final_timestamp_seconds;
  const displayTs = finalTs ?? preTs ?? null;
  const tone = disposition.toLowerCase().replaceAll("_", "-");

  return (
    <article
      className={`entry entry--assessment entry--${tone}${selected ? " is-selected" : ""}`}
      aria-current={selected ? "true" : undefined}
    >
      <h4 className="entry__title">
        <button type="button" className="entry__head" onClick={onSelect} aria-expanded={selected}>
          <span className="entry__index">{String(index + 1).padStart(2, "0")}</span>
          <DispositionBadge disposition={disposition} />
          <span className="entry__request">
            <span className="entry__text">{title}</span>
            <span className="entry__meta">
              {timecode(displayTs)} · {kind.toLowerCase()} · {change.confidence} confidence ·{" "}
              {selected ? "showing evidence" : "jump to moment"}
            </span>
          </span>
          <span className="entry__confidence entry__confidence--level">
            <ChangeKindBadge kind={kind} size="sm" />
          </span>
        </button>
      </h4>

      <div className="entry__body">
        <p className="entry__reason">{description}</p>

        <p className="entry__evidence-line">
          <span className="entry__tag">Disposition</span>
          <span>{explanation}</span>
        </p>

        {matchedRevisionTexts.length ? (
          <p className="entry__evidence-line">
            <span className="entry__tag">
              Matched {matchedRevisionTexts.length === 1 ? "revision" : "revisions"}
            </span>
            <span>{matchedRevisionTexts.map((text) => `“${text}”`).join(" · ")}</span>
          </p>
        ) : null}

        <p className="entry__evidence-line entry__timestamps">
          <span className="entry__tag">Evidence alignment</span>
          <span>
            Baseline: <b>{timecode(preTs)}</b>
          </span>
          <span>
            Candidate: <b>{timecode(finalTs)}</b>
          </span>
        </p>

        {selected ? (
          <>
            {evidence.window_start_pre_final != null && evidence.window_end_pre_final != null ? (
              <p className="disclosure__note">
                Baseline window: {timecode(evidence.window_start_pre_final, true)}–
                {timecode(evidence.window_end_pre_final, true)}
                {evidence.window_start_final != null && evidence.window_end_final != null ? (
                  <>
                    {" "}
                    · Candidate window: {timecode(evidence.window_start_final, true)}–
                    {timecode(evidence.window_end_final, true)}
                  </>
                ) : null}
              </p>
            ) : null}

            {evidence.text_before || evidence.text_after ? (
              <div className="semantic">
                <p className="semantic__head">Observed on-screen text</p>
                {evidence.text_before ? (
                  <p className="semantic__body">Baseline: {evidence.text_before}</p>
                ) : null}
                {evidence.text_after ? (
                  <p className="semantic__body">Candidate: {evidence.text_after}</p>
                ) : null}
              </div>
            ) : null}

            {evidence.pre_final_frame_path || evidence.final_frame_path ? (
              <div className="entry__frames">
                <EvidenceFrame
                  path={evidence.pre_final_frame_path}
                  label={`BASELINE · ${timecode(preTs)}`}
                  alt={`Baseline frame at ${timecode(preTs)} for ${title}`}
                />
                <EvidenceFrame
                  path={evidence.final_frame_path}
                  label={`CANDIDATE · ${timecode(finalTs)}`}
                  alt={`Release candidate frame at ${timecode(finalTs)} for ${title}`}
                />
              </div>
            ) : null}

            <details className="disclosure">
              <summary>Inspect evidence details</summary>
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
              {evidence.text_semantic_status ? (
                <p className="disclosure__note">
                  Text inspection: {evidence.text_semantic_status.replaceAll("_", " ")}
                </p>
              ) : null}
              {evidence.metrics?.length ? <MetricTable metrics={evidence.metrics} /> : null}
              <p className="disclosure__note">{evidence.explanation}</p>
            </details>
          </>
        ) : null}
      </div>
    </article>
  );
}
