"use client";

import { useMemo, useState } from "react";
import type { ChangeKind, DiscoverReport } from "../lib/types";
import { ChangeEntry } from "./ChangeEntry";
import { ChangeKindBadge } from "./ChangeKindBadge";
import { DiscoverComparisonViewer, type DiscoverMarkerItem } from "./DiscoverComparisonViewer";

type Props = {
  report: DiscoverReport;
  preFinalUrl: string | null;
  finalUrl: string | null;
  preFinalName: string;
  finalName: string;
  selectedId: string | null;
  seek: { preFinalTime: number; finalTime: number; nonce: number } | null;
  onSelect: (id: string) => void;
  onExport: () => void;
  exportState: "idle" | "working" | "error";
  exportNote: string;
};

type Filter = "ALL" | ChangeKind;

export function DiscoverReportSection({
  report,
  preFinalUrl,
  finalUrl,
  preFinalName,
  finalName,
  selectedId,
  seek,
  onSelect,
  onExport,
  exportState,
  exportNote,
}: Props) {
  const [filter, setFilter] = useState<Filter>("ALL");

  const markers: DiscoverMarkerItem[] = useMemo(
    () =>
      report.changes.map((c, i) => ({
        id: c.id,
        kind: c.kind,
        title: c.title,
        preFinalTime: c.evidence.pre_final_timestamp_seconds,
        finalTime: c.evidence.final_timestamp_seconds,
        index: i + 1,
      })),
    [report],
  );

  const selected = report.changes.find((c) => c.id === selectedId) ?? null;

  const visible = report.changes.filter((c) => filter === "ALL" || c.kind === filter);
  const total = report.changes.length;

  const kinds: ChangeKind[] = useMemo(() => {
    const list: ChangeKind[] = ["VISUAL", "TIMING", "AUDIO"];
    if (report.summary.text > 0) list.push("TEXT");
    list.push("REVIEW");
    return list;
  }, [report.summary.text]);

  const countOf = (k: ChangeKind) => {
    if (k === "VISUAL") return report.summary.visual;
    if (k === "TIMING") return report.summary.timing;
    if (k === "AUDIO") return report.summary.audio;
    if (k === "TEXT") return report.summary.text;
    if (k === "REVIEW") return report.summary.review;
    return 0;
  };

  const delta = report.duration_delta_seconds;
  const deltaText =
    Math.abs(delta) < 0.05
      ? "Durations match"
      : delta < 0
      ? `Final is ${Math.abs(delta).toFixed(1)}s shorter`
      : `Final is ${delta.toFixed(1)}s longer`;

  const selectedChangeInfo = selected
    ? {
        kind: selected.kind,
        title: selected.title,
        preFinalTime: selected.evidence.pre_final_timestamp_seconds,
        finalTime: selected.evidence.final_timestamp_seconds,
      }
    : null;

  return (
    <section className="report report--discover" aria-labelledby="discover-report-heading">
      <div className="shell">
        <div className="report__bar">
          <div className="report__identity">
            <span className="panel__index">03</span>
            <div>
              <h2 id="discover-report-heading">Change ledger</h2>
              <p>
                Report <b>{report.report_id.toUpperCase()}</b>
                {report.generated_at ? ` · ${new Date(report.generated_at).toLocaleString()}` : ""}
              </p>
            </div>
          </div>

          <ul className="report__tally report__tally--discover" aria-label="Change summary">
            <li>
              <b>{total}</b>
              <span className="report__tally-label">
                detected change{total === 1 ? "" : "s"}
              </span>
            </li>
            {kinds.map((k) => (
              <li key={k}>
                <b>{countOf(k)}</b>
                <ChangeKindBadge kind={k} size="sm" />
              </li>
            ))}
          </ul>

          <div className="report__sources report__sources--discover">
            <span>PRE-FINAL {preFinalName}</span>
            <span>FINAL {finalName}</span>
            <span className="report__delta-tag">{deltaText}</span>
          </div>

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
              {exportState === "working" ? "Exporting…" : "Export change ledger"}
            </button>
          </div>
        </div>

        <DiscoverComparisonViewer
          preFinalUrl={preFinalUrl}
          finalUrl={finalUrl}
          preFinalName={preFinalName}
          finalName={finalName}
          markers={markers}
          selectedId={selectedId}
          onSelect={onSelect}
          seek={seek}
          selectedChange={selectedChangeInfo}
        />

        <div className="report__body">
          <div className="report__subhead">
            <h3>Detected changes ({total})</h3>
            <div className="filters" role="group" aria-label="Filter changes by kind">
              <button
                type="button"
                className={`btn btn--filter ${filter === "ALL" ? "is-active" : ""}`}
                onClick={() => setFilter("ALL")}
              >
                All ({total})
              </button>
              {kinds.map((k) => (
                <button
                  key={k}
                  type="button"
                  className={`btn btn--filter ${filter === k ? "is-active" : ""}`}
                  onClick={() => setFilter(k)}
                >
                  {k.charAt(0) + k.slice(1).toLowerCase()} ({countOf(k)})
                </button>
              ))}
            </div>
          </div>

          {total === 0 ? (
            <div className="zero-changes" role="status">
              <div className="zero-changes__icon" aria-hidden="true">✓</div>
              <h4>NO MEANINGFUL CHANGES DETECTED</h4>
              <p className="zero-changes__lead">
                EditDiff did not find visual, timing, or audio differences above the current evidence thresholds.
              </p>
              <p className="zero-changes__sub">
                Sub-sample edits and subtle typography changes may require manual review.
              </p>
            </div>
          ) : visible.length === 0 ? (
            <p className="ledger__none" role="status">
              No changes matched the <b>{filter}</b> filter.
            </p>
          ) : (
            <div className="ledger" role="feed" aria-label="Change entries">
              {visible.map((change, i) => (
                <ChangeEntry
                  key={change.id}
                  change={change}
                  index={i}
                  selected={selectedId === change.id}
                  onSelect={() => onSelect(change.id)}
                />
              ))}
            </div>
          )}

          {exportNote ? (
            <p
              className={`report__note ${
                exportState === "error" ? "report__note--error" : ""
              }`}
              role="status"
            >
              {exportNote}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
