"use client";

import { timecode } from "../lib/format";
import type { DetectedChange } from "../lib/types";
import { ChangeKindBadge } from "./ChangeKindBadge";
import { EvidenceFrame } from "./EvidenceFrame";
import { MetricTable } from "./MetricTable";

type Props = {
  change: DetectedChange;
  index: number;
  selected: boolean;
  onSelect: () => void;
};

const REASON_LABELS: Record<string, string> = {
  segment_removed_with_aligned_flanks: "Segment cut with verified flanking footage",
  segment_inserted_with_aligned_flanks: "Segment inserted with verified flanking footage",
  timing_change_single_flank: "Timing shift verified on single flank",
  timing_alignment_ambiguous: "Timing discrepancy with ambiguous alignment",
  aligned_visual_difference: "Material visual difference in aligned window",
  local_audio_muted: "Audio muted in aligned window (>75% reduction)",
  local_audio_added: "Active audio introduced in previously silent window",
  local_audio_energy_shifted: "Material audio energy shift in aligned window",
  timeline_divergence_exceeds_band: "Timeline divergence exceeds automatic search band",
  alignment_band_boundary_encountered: "Alignment approached search boundary",
};

export function ChangeEntry({ change, index, selected, onSelect }: Props) {
  const { kind, confidence, title, description, evidence } = change;

  const preTs = evidence.pre_final_timestamp_seconds;
  const finalTs = evidence.final_timestamp_seconds;
  const displayTs = finalTs ?? preTs ?? null;

  const primaryReason = evidence.reason_codes?.[0] ?? "";
  const reasonLabel = REASON_LABELS[primaryReason] || primaryReason.replaceAll("_", " ");

  const kindTone = kind.toLowerCase();

  return (
    <article
      className={`entry entry--discover entry--${kindTone}${selected ? " is-selected" : ""}`}
      aria-current={selected ? "true" : undefined}
    >
      <h3 className="entry__title">
        <button type="button" className="entry__head" onClick={onSelect} aria-expanded={selected}>
          <span className="entry__index">{String(index + 1).padStart(2, "0")}</span>
          <ChangeKindBadge kind={kind} />
          <span className="entry__request">
            <span className="entry__text">{title}</span>
            <span className="entry__meta">
              {timecode(displayTs)} · {confidence} confidence ·{" "}
              {selected ? "showing evidence" : "jump to moment"}
            </span>
          </span>
          <span className="entry__confidence entry__confidence--level">
            <b>{confidence}</b>
            <span>confidence</span>
          </span>
        </button>
      </h3>

      <div className="entry__body">
        <p className="entry__reason">{description}</p>

        {primaryReason ? (
          <p className="entry__evidence-line">
            <span className="entry__tag">Reason</span> {reasonLabel}
          </p>
        ) : null}

        <p className="entry__evidence-line entry__timestamps">
          <span className="entry__tag">Evidence alignment</span>
          <span>Pre-final: <b>{timecode(preTs)}</b></span>
          <span>Final: <b>{timecode(finalTs)}</b></span>
        </p>

        {selected ? (
          <>
            {evidence.window_start_pre_final != null && evidence.window_end_pre_final != null ? (
              <p className="disclosure__note">
                Pre-final window: {timecode(evidence.window_start_pre_final, true)}–{timecode(evidence.window_end_pre_final, true)}
                {evidence.window_start_final != null && evidence.window_end_final != null ? (
                  <> · Final window: {timecode(evidence.window_start_final, true)}–{timecode(evidence.window_end_final, true)}</>
                ) : null}
              </p>
            ) : null}

            {evidence.pre_final_frame_path || evidence.final_frame_path ? (
              <div className="entry__frames">
                <EvidenceFrame
                  path={evidence.pre_final_frame_path}
                  label={`PRE-FINAL EVIDENCE · ${timecode(preTs)}`}
                  alt={`Pre-final export frame at ${timecode(preTs)} for ${title}`}
                />
                <EvidenceFrame
                  path={evidence.final_frame_path}
                  label={`FINAL EVIDENCE · ${timecode(finalTs)}`}
                  alt={`Final export frame at ${timecode(finalTs)} for ${title}`}
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
              {evidence.metrics?.length ? <MetricTable metrics={evidence.metrics} /> : null}
              <p className="disclosure__note">{evidence.explanation}</p>
            </details>
          </>
        ) : null}
      </div>
    </article>
  );
}
