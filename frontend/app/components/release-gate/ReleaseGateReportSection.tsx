"use client";

import { useMemo } from "react";
import { timecode } from "../../lib/format";
import { DECISION_GLYPH, type ReleaseGateResult } from "../../lib/releaseGate";
import { EvidenceEntry } from "../EvidenceEntry";
import { VerdictBadge } from "../VerdictBadge";
import { ChangeAssessmentEntry } from "./ChangeAssessmentEntry";
import { ReleaseDecisionBanner } from "./ReleaseDecisionBanner";
import { ReleaseGateComparisonViewer, type GateMarker } from "./ReleaseGateComparisonViewer";
import { TechnicalCheckEntry } from "./TechnicalCheckEntry";

export type GateSelection = string | null;

type Props = {
  result: ReleaseGateResult;
  baselineUrl: string | null;
  candidateUrl: string | null;
  baselineName: string;
  candidateName: string;
  selectedId: GateSelection;
  seek: { baselineTime: number; candidateTime: number; nonce: number } | null;
  onSelect: (id: string) => void;
  onExport: () => void;
  exportState: "idle" | "working" | "error";
  exportNote: string;
};

/** Group-prefixed marker / row ids: the three lists have independent id spaces. */
export const REVISION_PREFIX = "rev:";
export const CHANGE_PREFIX = "chg:";
export const TECHNICAL_PREFIX = "tec:";

export function ReleaseGateReportSection({
  result,
  baselineUrl,
  candidateUrl,
  baselineName,
  candidateName,
  selectedId,
  seek,
  onSelect,
  onExport,
  exportState,
  exportNote,
}: Props) {
  const { requested_revisions, change_assessments, technical_checks, summary } = result;

  const revisionTextById = useMemo(() => {
    const map = new Map<string, string>();
    for (const r of requested_revisions) map.set(r.request.id, r.request.raw_text);
    return map;
  }, [requested_revisions]);

  const markers: GateMarker[] = useMemo(() => {
    const out: GateMarker[] = [];

    requested_revisions.forEach((r, i) => {
      const seconds = r.evidence.timestamp_seconds ?? r.request.timestamp_seconds;
      if (seconds == null) return;
      out.push({
        id: `${REVISION_PREFIX}${r.request.id}`,
        seconds,
        tone: r.verdict.toLowerCase(),
        glyph: r.verdict === "PASS" ? "✓" : r.verdict === "FAIL" ? "✕" : "?",
        label: r.request.raw_text,
        group: "Requested revision",
        index: i + 1,
      });
    });

    change_assessments.forEach((c, i) => {
      const seconds =
        c.evidence.final_timestamp_seconds ?? c.evidence.pre_final_timestamp_seconds;
      if (seconds == null) return;
      out.push({
        id: `${CHANGE_PREFIX}${c.id}`,
        seconds,
        tone: c.disposition.toLowerCase().replaceAll("_", "-"),
        glyph: c.disposition === "UNEXPECTED" ? "!" : c.disposition === "REVIEW" ? "?" : "✓",
        label: c.title,
        group: "Detected change",
        index: i + 1,
      });
    });

    technical_checks.forEach((t, i) => {
      if (t.timestamp_seconds == null) return;
      out.push({
        id: `${TECHNICAL_PREFIX}${t.id}`,
        seconds: t.timestamp_seconds,
        tone: `tech-${t.status.toLowerCase().replaceAll("_", "-")}`,
        glyph: t.status === "PASS" ? "✓" : t.status === "FAIL" ? "✕" : "?",
        label: t.name,
        group: "Technical check",
        index: i + 1,
      });
    });

    return out.sort((a, b) => a.seconds - b.seconds);
  }, [requested_revisions, change_assessments, technical_checks]);

  const caption = useMemo(() => {
    if (!selectedId) return null;
    const marker = markers.find((m) => m.id === selectedId);
    if (!marker) return null;
    return {
      label: marker.label,
      group: marker.group,
      tone: marker.tone,
      seconds: marker.seconds,
    };
  }, [markers, selectedId]);

  const unresolved =
    summary.unexpected_changes + summary.change_association_review + summary.requested_failed;

  return (
    <>
      <ReleaseDecisionBanner result={result} />

      <section className="report report--gate" aria-labelledby="gate-report-heading">
        <div className="shell">
          <div className="report__bar">
            <div className="report__identity">
              <span className="panel__index">03</span>
              <div>
                <h2 id="gate-report-heading">Release evidence</h2>
                <p>
                  Report <b>{result.report_id.toUpperCase()}</b>
                </p>
              </div>
            </div>

            <p className="report__sources">
              <span>BASELINE {baselineName}</span>
              <span>CANDIDATE {candidateName}</span>
            </p>

            <div className="report__actions">
              <button type="button" className="btn btn--ghost" onClick={() => window.print()}>
                Print / PDF
              </button>
              <button
                type="button"
                className="btn btn--export"
                onClick={onExport}
                disabled={exportState === "working"}
              >
                {exportState === "working" ? "Exporting…" : "Export release record"}
              </button>
            </div>
          </div>

          {exportNote ? (
            <p
              className={`report__note ${exportState === "error" ? "report__note--error" : ""}`}
              role="status"
            >
              {exportNote}
            </p>
          ) : null}

          <ReleaseGateComparisonViewer
            baselineUrl={baselineUrl}
            candidateUrl={candidateUrl}
            markers={markers}
            selectedId={selectedId}
            onSelect={onSelect}
            seek={seek}
            caption={caption}
          />
          <p className="report__hint">
            Every marker on the rail is one finding. Pick one to jump both exports to the moment it
            was measured, then open it below for the evidence behind it.
          </p>

          <DecisionReasons result={result} />

          {/* ---------------------------------------------- requested revisions */}
          <section className="gate-block" aria-labelledby="gate-requested">
            <div className="report__subhead">
              <h3 id="gate-requested">Requested revisions ({summary.requested_total})</h3>
              <p className="gate-block__tally">
                <VerdictBadge verdict="PASS" size="sm" /> {summary.requested_passed}
                <VerdictBadge verdict="FAIL" size="sm" /> {summary.requested_failed}
                <VerdictBadge verdict="REVIEW" size="sm" /> {summary.requested_review}
              </p>
            </div>

            {requested_revisions.length === 0 ? (
              <p className="gate-empty">
                No revision notes were submitted with this release candidate, so the gate has no
                requested revisions to verify. Detected changes below were assessed without them.
              </p>
            ) : (
              <div className="ledger">
                {requested_revisions.map((r, i) => (
                  <EvidenceEntry
                    key={r.request.id}
                    result={r}
                    index={i}
                    selected={selectedId === `${REVISION_PREFIX}${r.request.id}`}
                    onSelect={() => onSelect(`${REVISION_PREFIX}${r.request.id}`)}
                  />
                ))}
              </div>
            )}
          </section>

          {/* ------------------------------------------------ change assessment */}
          <section className="gate-block" aria-labelledby="gate-changes">
            <div className="report__subhead">
              <h3 id="gate-changes">
                Unexpected and unresolved changes ({summary.unexpected_changes +
                  summary.change_association_review}
                )
              </h3>
              <p className="gate-block__tally muted">
                {change_assessments.length} detected change
                {change_assessments.length === 1 ? "" : "s"} assessed ·{" "}
                {summary.accounted_changes} accounted for
              </p>
            </div>

            {change_assessments.length === 0 ? (
              <p className="gate-empty">
                No changes were detected between the baseline and the release candidate above
                current thresholds. Sub-sample edits and subtle typography changes may require
                manual review.
              </p>
            ) : (
              <div className="ledger">
                {change_assessments.map((c, i) => (
                  <ChangeAssessmentEntry
                    key={c.id}
                    assessment={c}
                    index={i}
                    selected={selectedId === `${CHANGE_PREFIX}${c.id}`}
                    associatedRevisionText={
                      c.associated_revision_id
                        ? revisionTextById.get(c.associated_revision_id) ?? null
                        : null
                    }
                    onSelect={() => onSelect(`${CHANGE_PREFIX}${c.id}`)}
                  />
                ))}
              </div>
            )}
          </section>

          {/* --------------------------------------------------- technical QA */}
          <section className="gate-block" aria-labelledby="gate-technical">
            <div className="report__subhead">
              <h3 id="gate-technical">Technical QA ({technical_checks.length})</h3>
              <p className="gate-block__tally muted">
                {summary.technical_passed} passing · {summary.technical_failed} failing ·{" "}
                {summary.technical_review} review
              </p>
            </div>

            {technical_checks.length === 0 ? (
              <p className="gate-empty">
                This API build ran no technical checks on the release candidate.
              </p>
            ) : (
              <div className="ledger">
                {technical_checks.map((t, i) => (
                  <TechnicalCheckEntry
                    key={t.id}
                    check={t}
                    index={i}
                    selected={selectedId === `${TECHNICAL_PREFIX}${t.id}`}
                    onSelect={() => onSelect(`${TECHNICAL_PREFIX}${t.id}`)}
                  />
                ))}
              </div>
            )}
          </section>

          <p className="ledger__foot">
            {unresolved === 0
              ? "No unresolved changes detected above current thresholds. Release Gate reports what it can measure; it does not certify what it did not sample."
              : `${unresolved} finding${unresolved === 1 ? "" : "s"} stand between this candidate and a clean gate.`}{" "}
            Baseline {timecode(result.baseline_duration_seconds, true)} · candidate{" "}
            {timecode(result.candidate_duration_seconds, true)}.
          </p>
        </div>
      </section>
    </>
  );
}

function DecisionReasons({ result }: { result: ReleaseGateResult }) {
  if (!result.decision_reasons.length) return null;
  const tone = result.decision.toLowerCase().replaceAll("_", "-");
  return (
    <section className={`reasons reasons--${tone}`} aria-labelledby="gate-reasons">
      <h3 id="gate-reasons">
        <span className="reasons__glyph" aria-hidden="true">
          {DECISION_GLYPH[result.decision]}
        </span>
        Why the gate reached this decision
      </h3>
      <ol className="reasons__list">
        {result.decision_reasons.map((reason, i) => (
          <li key={`${i}-${reason}`}>
            <span className="reasons__index">{String(i + 1).padStart(2, "0")}</span>
            <span>{reason}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
