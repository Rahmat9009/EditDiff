import { VERDICTS, type Report, type Verdict } from "../lib/types";
import { AnalysisStages } from "./AnalysisStages";
import { VerdictBadge } from "./VerdictBadge";

type Props = { busy: boolean; report: Report | null };

function count(report: Report, verdict: Verdict): number {
  return Number(report.summary?.[verdict] ?? 0);
}

export function StatusPanel({ busy, report }: Props) {
  return (
    <aside className="panel status" aria-labelledby="status-heading">
      <div className="panel__head">
        <span className="panel__index">02</span>
        <h2 id="status-heading">Revision score</h2>
      </div>

      {busy ? (
        <AnalysisStages />
      ) : !report ? (
        <div className="status__empty">
          <div className="status__target" aria-hidden="true">
            <span />
            <span />
          </div>
          <p className="status__empty-lead">No audit yet.</p>
          <p className="status__empty-note">
            Every revision note becomes one checked line here, with a verdict, a timestamp and the
            before/after evidence behind it.
          </p>
        </div>
      ) : (
        <ScoreBody report={report} />
      )}
    </aside>
  );
}

function ScoreBody({ report }: { report: Report }) {
  const total = report.results.length || 1;
  const pass = count(report, "PASS");
  const fail = count(report, "FAIL");
  const review = count(report, "REVIEW");

  return (
    <div className="score">
      <p className="score__figure">
        <strong>{pass}</strong>
        <span>
          of {report.results.length} requested revision{report.results.length === 1 ? "" : "s"}
          <br />
          verified by evidence
        </span>
      </p>

      <div className="score__ratio" role="img" aria-label={`${pass} pass, ${fail} fail, ${review} review`}>
        {(
          [
            ["PASS", pass],
            ["FAIL", fail],
            ["REVIEW", review],
          ] as const
        ).map(([verdict, value]) =>
          value > 0 ? (
            <span
              key={verdict}
              className={`score__seg score__seg--${verdict.toLowerCase()}`}
              style={{ flexGrow: value / total }}
            />
          ) : null,
        )}
      </div>

      <ul className="score__counts">
        {VERDICTS.map((v) => (
          <li key={v}>
            <b>{count(report, v)}</b>
            <VerdictBadge verdict={v} size="sm" />
          </li>
        ))}
      </ul>

      {fail > 0 ? (
        <p className="score__call score__call--fail">
          {fail} requested revision{fail === 1 ? "" : "s"} did not land. Send the ledger back to your
          editor.
          {review > 0
            ? ` ${review} more need${review === 1 ? "s" : ""} a human eye before you sign off.`
            : ""}
        </p>
      ) : review > 0 ? (
        <p className="score__call">
          {review} item{review === 1 ? "" : "s"} need a human eye — EditDiff will not claim certainty
          it cannot prove.
        </p>
      ) : (
        <p className="score__call score__call--pass">
          Every requested revision is supported by evidence. This cut is clear to ship.
        </p>
      )}

      <p className="score__id">
        Report <b>{report.report_id.toUpperCase()}</b>
      </p>
    </div>
  );
}
