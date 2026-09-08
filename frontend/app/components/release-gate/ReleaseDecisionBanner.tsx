import { timecode } from "../../lib/format";
import {
  DECISION_GLYPH,
  DECISION_LABEL,
  DECISION_MEANING,
  type ReleaseGateResult,
} from "../../lib/releaseGate";

/**
 * The one element on the page that has to command it. Dark ground, one status
 * colour, no hedging — and no claim that the export is "safe", only what the
 * evidence did and did not establish.
 */
export function ReleaseDecisionBanner({ result }: { result: ReleaseGateResult }) {
  const { decision, summary } = result;
  const tone = decision.toLowerCase().replaceAll("_", "-");
  const delta = result.candidate_duration_seconds - result.baseline_duration_seconds;
  const deltaText =
    Math.abs(delta) < 0.05
      ? "Durations match"
      : delta < 0
        ? `Candidate is ${Math.abs(delta).toFixed(1)}s shorter`
        : `Candidate is ${delta.toFixed(1)}s longer`;

  return (
    <section className={`decision decision--${tone}`} aria-labelledby="decision-heading">
      <div className="shell decision__inner">
        <p className="decision__eyebrow">Release decision</p>
        <h2 id="decision-heading" className="decision__verdict">
          <span className="decision__glyph" aria-hidden="true">
            {DECISION_GLYPH[decision]}
          </span>
          {DECISION_LABEL[decision]}
        </h2>
        <p className="decision__meaning">{DECISION_MEANING[decision]}</p>

        <dl className="decision__tally">
          <div>
            <dt>Requested revisions</dt>
            <dd>
              <b>{summary.requested_passed}</b>
              <span>
                of {summary.requested_total} verified
                {summary.requested_failed > 0 ? ` · ${summary.requested_failed} failed` : ""}
                {summary.requested_review > 0 ? ` · ${summary.requested_review} review` : ""}
              </span>
            </dd>
          </div>
          <div>
            <dt>Unexpected changes</dt>
            <dd>
              <b>{summary.unexpected_changes}</b>
              <span>
                {summary.accounted_changes} accounted for
                {summary.change_association_review > 0
                  ? ` · ${summary.change_association_review} unresolved`
                  : ""}
              </span>
            </dd>
          </div>
          <div>
            <dt>Technical QA</dt>
            <dd>
              <b>{summary.technical_failed}</b>
              <span>
                failing · {summary.technical_passed} passing
                {summary.technical_review > 0 ? ` · ${summary.technical_review} review` : ""}
              </span>
            </dd>
          </div>
        </dl>

        <p className="decision__meta">
          <span>REPORT {result.report_id.toUpperCase()}</span>
          <span>
            BASELINE {timecode(result.baseline_duration_seconds, true)} · CANDIDATE{" "}
            {timecode(result.candidate_duration_seconds, true)}
          </span>
          <span>{deltaText}</span>
        </p>
      </div>
    </section>
  );
}
