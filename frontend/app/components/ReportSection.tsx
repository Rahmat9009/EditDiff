"use client";

import { useMemo, useState } from "react";
import { timecode } from "../lib/format";
import { VERDICTS, type Report, type Verdict } from "../lib/types";
import { ComparisonViewer } from "./ComparisonViewer";
import { EvidenceEntry } from "./EvidenceEntry";
import type { Marker } from "./TimelineRail";
import { VerdictBadge } from "./VerdictBadge";

type Props = {
  report: Report;
  v1Url: string | null;
  v2Url: string | null;
  v1Name: string;
  v2Name: string;
  selectedId: string | null;
  seek: { time: number; nonce: number } | null;
  onSelect: (id: string) => void;
  onExport: () => void;
  exportState: "idle" | "working" | "error";
  exportNote: string;
};

type Filter = "ALL" | Verdict;

export function ReportSection({
  report,
  v1Url,
  v2Url,
  v1Name,
  v2Name,
  selectedId,
  seek,
  onSelect,
  onExport,
  exportState,
  exportNote,
}: Props) {
  const [filter, setFilter] = useState<Filter>("ALL");

  const markers: Marker[] = useMemo(
    () =>
      report.results.map((r, i) => ({
        id: r.request.id,
        seconds: r.evidence.timestamp_seconds ?? r.request.timestamp_seconds ?? 0,
        verdict: r.verdict,
        label: r.request.raw_text,
        index: i + 1,
      })),
    [report],
  );

  const selected = report.results.find((r) => r.request.id === selectedId) ?? null;
  const visible = report.results.filter((r) => filter === "ALL" || r.verdict === filter);
  const total = report.results.length;
  const countOf = (v: Verdict) => Number(report.summary?.[v] ?? 0);
  const spanStart = Math.min(...markers.map((m) => m.seconds));
  const spanEnd = Math.max(...markers.map((m) => m.seconds));

  return (
    <section className="report" aria-labelledby="report-heading">
      <div className="shell">
        <div className="report__bar">
          <div className="report__identity">
            <span className="panel__index">03</span>
            <div>
              <h2 id="report-heading">Evidence ledger</h2>
              <p>
                Report <b>{report.report_id.toUpperCase()}</b>
                {report.generated_at ? ` · ${new Date(report.generated_at).toLocaleString()}` : ""}
              </p>
            </div>
          </div>

          <ul className="report__tally" aria-label="Verdict summary">
            <li>
              <b>{total}</b>
              <span className="report__tally-label">
                requested revision{total === 1 ? "" : "s"}
              </span>
            </li>
            {VERDICTS.map((v) => (
              <li key={v}>
                <b>{countOf(v)}</b>
                <VerdictBadge verdict={v} size="sm" />
              </li>
            ))}
          </ul>

          <p className="report__sources">
            <span>V1 {v1Name}</span>
            <span>V2 {v2Name}</span>
          </p>
          <div className="report__actions">
            <button type="button" className="btn btn--ghost" onClick={() => window.print()}>
              Print / PDF
            </button>
            <button
              type="button"
              className="btn btn--ghost"
              onClick={onExport}
              disabled={exportState === "working"}
            >
              {exportState === "working" ? "Exporting…" : "Export audit"}
            </button>
          </div>
        </div>
        {exportNote ? (
          <p className="report__note" role="status">
            {exportNote}
          </p>
        ) : null}
      </div>

      <div className="shell report__grid">
        <div className="report__viewer">
          <ComparisonViewer
            v1Url={v1Url}
            v2Url={v2Url}
            markers={markers}
            selectedId={selectedId}
            onSelect={onSelect}
            seek={seek}
            caption={
              selected
                ? {
                    label: selected.request.raw_text,
                    verdict: selected.verdict,
                    seconds:
                      selected.evidence.timestamp_seconds ?? selected.request.timestamp_seconds ?? null,
                  }
                : null
            }
          />
          <p className="report__hint">
            Pick any revision to jump both exports to its timestamp. Markers on the rail carry the
            verdict.
          </p>
        </div>

        <div className="report__ledger">
          <div className="filters" role="group" aria-label="Filter revisions by verdict">
            {(["ALL", ...VERDICTS] as Filter[]).map((f) => {
              const n =
                f === "ALL" ? report.results.length : report.results.filter((r) => r.verdict === f).length;
              return (
                <button
                  key={f}
                  type="button"
                  className={`filter${filter === f ? " is-active" : ""}`}
                  onClick={() => setFilter(f)}
                  aria-pressed={filter === f}
                >
                  {f === "ALL" ? "All" : f}
                  <span>{n}</span>
                </button>
              );
            })}
          </div>

          {visible.length === 0 ? (
            <p className="muted ledger__empty">No revisions with this verdict.</p>
          ) : (
            <div className="ledger">
              {visible.map((r) => (
                <EvidenceEntry
                  key={r.request.id}
                  result={r}
                  index={report.results.indexOf(r)}
                  selected={r.request.id === selectedId}
                  onSelect={() => onSelect(r.request.id)}
                />
              ))}
            </div>
          )}

          <p className="ledger__foot">
            {total} requested revision{total === 1 ? "" : "s"} checked between{" "}
            {timecode(spanStart, spanStart % 1 !== 0)} and {timecode(spanEnd, spanEnd % 1 !== 0)}.{" "}
            <VerdictBadge verdict="REVIEW" size="sm" /> means the available evidence cannot
            establish whether the requested edit landed — EditDiff records that instead of a pass.
          </p>
        </div>
      </div>
    </section>
  );
}
