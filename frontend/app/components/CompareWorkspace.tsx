"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  analyze,
  ApiError,
  discoverChanges,
  fetchAuditExport,
  fetchDiscoverExport,
} from "../lib/api";
import { downloadBlob } from "../lib/download";
import { useApiHealthContext } from "../lib/useApiHealth";
import { VERDICT_MEANING } from "../lib/format";
import { VERDICTS, type DiscoverReport, type Report } from "../lib/types";
import type { MediaMeta, MediaSlot } from "./DropZone";
import { DiscoverIntakePanel } from "./DiscoverIntakePanel";
import { DiscoverReportSection } from "./DiscoverReportSection";
import { DiscoverStatusPanel } from "./DiscoverStatusPanel";
import { IntakePanel } from "./IntakePanel";
import { ReportSection } from "./ReportSection";
import { StatusPanel } from "./StatusPanel";
import { VerdictBadge } from "./VerdictBadge";
import { WorkflowModeSelector, type WorkflowMode } from "./WorkflowModeSelector";

type Slots = { v1: MediaSlot | null; v2: MediaSlot | null };

/**
 * Compare Versions. Verify Revisions and Discover Changes are two modes of one
 * page: the exports and the notes survive a mode switch, only the result does
 * not. Analysis behaviour is unchanged from the single-page build.
 */
export function CompareWorkspace() {
  const { reportApiState } = useApiHealthContext();
  const searchParams = useSearchParams();
  const initialMode: WorkflowMode = searchParams.get("mode") === "discover" ? "discover" : "verify";

  const [mode, setMode] = useState<WorkflowMode>(initialMode);
  const [slots, setSlots] = useState<Slots>({ v1: null, v2: null });
  const [metas, setMetas] = useState<{ v1: MediaMeta | null; v2: MediaMeta | null }>({
    v1: null,
    v2: null,
  });
  const [notes, setNotes] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [discoverReport, setDiscoverReport] = useState<DiscoverReport | null>(null);

  const [busy, setBusy] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);
  const [error, setError] = useState("");

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [seek, setSeek] = useState<{ time: number; nonce: number } | null>(null);

  const [discoverSelectedId, setDiscoverSelectedId] = useState<string | null>(null);
  const [discoverSeek, setDiscoverSeek] = useState<{
    preFinalTime: number;
    finalTime: number;
    nonce: number;
  } | null>(null);

  const [exportState, setExportState] = useState<"idle" | "working" | "error">("idle");
  const [exportNote, setExportNote] = useState("");

  const slotsRef = useRef(slots);
  slotsRef.current = slots;
  const nonce = useRef(0);
  const reportRef = useRef<HTMLDivElement>(null);

  /* Revoke every object URL still alive when the page unmounts. */
  useEffect(
    () => () => {
      const { v1, v2 } = slotsRef.current;
      if (v1) URL.revokeObjectURL(v1.url);
      if (v2) URL.revokeObjectURL(v2.url);
    },
    [],
  );

  const reportId = mode === "verify" ? report?.report_id ?? null : discoverReport?.report_id ?? null;
  useEffect(() => {
    if (!reportId) return;
    const frame = window.requestAnimationFrame(() => {
      const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      reportRef.current?.scrollIntoView({
        behavior: still ? "auto" : "smooth",
        block: "start",
      });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [reportId]);

  const handleModeChange = useCallback((nextMode: WorkflowMode) => {
    setMode(nextMode);
    // Clear displayed result state and selections, but preserve uploaded files and notes
    setReport(null);
    setDiscoverReport(null);
    setSelectedId(null);
    setDiscoverSelectedId(null);
    setSeek(null);
    setDiscoverSeek(null);
    setError("");
    setExportNote("");
  }, []);

  const setFile = useCallback((role: "v1" | "v2", file: File | null) => {
    setReport(null);
    setDiscoverReport(null);
    setSelectedId(null);
    setDiscoverSelectedId(null);
    setSeek(null);
    setDiscoverSeek(null);
    setExportNote("");
    setMetas((prev) => ({ ...prev, [role]: null }));
    setSlots((prev) => {
      const current = prev[role];
      if (current) URL.revokeObjectURL(current.url);
      return { ...prev, [role]: file ? { file, url: URL.createObjectURL(file) } : null };
    });
  }, []);

  const setMeta = useCallback((role: "v1" | "v2", meta: MediaMeta | null) => {
    setMetas((prev) => ({ ...prev, [role]: meta }));
  }, []);

  const select = useCallback(
    (id: string) => {
      setSelectedId(id);
      const result = report?.results.find((r) => r.request.id === id);
      const time = result?.evidence.timestamp_seconds ?? result?.request.timestamp_seconds ?? null;
      if (time !== null && time !== undefined) {
        nonce.current += 1;
        setSeek({ time, nonce: nonce.current });
      }
    },
    [report],
  );

  const selectDiscover = useCallback(
    (id: string) => {
      setDiscoverSelectedId(id);
      const change = discoverReport?.changes.find((c) => c.id === id);
      if (!change) return;
      const preTs = change.evidence.pre_final_timestamp_seconds ?? change.evidence.final_timestamp_seconds ?? 0;
      const finalTs = change.evidence.final_timestamp_seconds ?? change.evidence.pre_final_timestamp_seconds ?? 0;
      nonce.current += 1;
      setDiscoverSeek({
        preFinalTime: preTs,
        finalTime: finalTs,
        nonce: nonce.current,
      });
    },
    [discoverReport],
  );

  const loadDemo = useCallback(async () => {
    setDemoBusy(true);
    setError("");
    try {
      const [a, b, noteFile] = await Promise.all([
        fetch("/demo/demo-v1.mp4"),
        fetch("/demo/demo-v2.mp4"),
        fetch("/demo/edit-notes.txt"),
      ]);
      if (!a.ok || !b.ok || !noteFile.ok) throw new Error("Demo assets are missing from this build.");
      const [blobA, blobB, demoNotes] = await Promise.all([a.blob(), b.blob(), noteFile.text()]);
      setFile("v1", new File([blobA], "demo-v1.mp4", { type: "video/mp4" }));
      setFile("v2", new File([blobB], "demo-v2.mp4", { type: "video/mp4" }));
      /* Trailing newline would scroll the five demo requests out of view. */
      setNotes(demoNotes.replace(/\s+$/, ""));
      setReport(null);
      setDiscoverReport(null);
      setSelectedId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the demo files.");
    } finally {
      setDemoBusy(false);
    }
  }, [setFile]);

  const runVerify = useCallback(async () => {
    const { v1, v2 } = slotsRef.current;
    if (!v1 || !v2) {
      setError("Add both the previous and the revised export.");
      return;
    }
    if (!notes.trim()) {
      setError("Add at least one revision note.");
      return;
    }
    setBusy(true);
    setError("");
    setReport(null);
    setSelectedId(null);
    setExportNote("");
    try {
      const next = await analyze(v1.file, v2.file, notes);
      setReport(next);
      reportApiState(true);
      const first = next.results[0];
      if (first) {
        setSelectedId(first.request.id);
        const time = first.evidence.timestamp_seconds ?? first.request.timestamp_seconds ?? null;
        if (time !== null && time !== undefined) {
          nonce.current += 1;
          setSeek({ time, nonce: nonce.current });
        }
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        if (err.offline) reportApiState(false);
      } else {
        setError(err instanceof Error ? err.message : "Analysis failed.");
      }
    } finally {
      setBusy(false);
    }
  }, [notes, reportApiState]);

  const runDiscover = useCallback(async () => {
    const { v1, v2 } = slotsRef.current;
    if (!v1 || !v2) {
      setError("Add both the pre-final and the final export.");
      return;
    }
    setBusy(true);
    setError("");
    setDiscoverReport(null);
    setDiscoverSelectedId(null);
    setExportNote("");
    try {
      const next = await discoverChanges(v1.file, v2.file);
      setDiscoverReport(next);
      reportApiState(true);
      const first = next.changes[0];
      if (first) {
        setDiscoverSelectedId(first.id);
        const preTs = first.evidence.pre_final_timestamp_seconds ?? first.evidence.final_timestamp_seconds ?? 0;
        const finalTs = first.evidence.final_timestamp_seconds ?? first.evidence.pre_final_timestamp_seconds ?? 0;
        nonce.current += 1;
        setDiscoverSeek({
          preFinalTime: preTs,
          finalTime: finalTs,
          nonce: nonce.current,
        });
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        if (err.offline) reportApiState(false);
      } else {
        setError(err instanceof Error ? err.message : "Discovery failed.");
      }
    } finally {
      setBusy(false);
    }
  }, [reportApiState]);

  const exportAudit = useCallback(async () => {
    if (!report) return;
    setExportState("working");
    setExportNote("");
    try {
      const remote = await fetchAuditExport(report);
      const blob =
        remote ?? new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
      downloadBlob(blob, `editdiff-${report.report_id}.json`);
      setExportState("idle");
      setExportNote(
        remote
          ? "Audit JSON downloaded from the API."
          : "The API export could not be reached or validated. Downloaded the report already in this browser as JSON.",
      );
    } catch {
      setExportState("error");
      setExportNote("Export failed. Print / PDF still works offline.");
    }
  }, [report]);

  const exportDiscover = useCallback(async () => {
    if (!discoverReport) return;
    setExportState("working");
    setExportNote("");
    try {
      const remote = await fetchDiscoverExport(discoverReport);
      const blob =
        remote ??
        new Blob([JSON.stringify(discoverReport, null, 2)], { type: "application/json" });
      downloadBlob(blob, `editdiff-changes-${discoverReport.report_id}.json`);
      setExportState("idle");
      setExportNote(
        remote
          ? "Change ledger JSON downloaded from the API."
          : "The API export could not be reached. Downloaded the report already in this browser as JSON.",
      );
    } catch {
      setExportState("error");
      setExportNote("Export failed. Print / PDF still works offline.");
    }
  }, [discoverReport]);

  return (
    <>
      <header className="page-head">
        <div className="shell page-head__inner">
          <div>
            <p className="eyebrow">Compare Versions</p>
            <h1>Understand exactly what changed.</h1>
            <p className="lede">
              Verify that the requested edits landed, or discover everything that changed between
              two exports. Both return a timestamped ledger with the evidence behind it.
            </p>
          </div>
          <dl className="legend" aria-label="What each verdict means">
            {VERDICTS.map((v) => (
              <div key={v}>
                <dt>
                  <VerdictBadge verdict={v} size="sm" />
                </dt>
                <dd>{VERDICT_MEANING[v]}</dd>
              </div>
            ))}
          </dl>
        </div>
      </header>

      <div className="shell">
        <WorkflowModeSelector mode={mode} onChange={handleModeChange} disabled={busy || demoBusy} />
      </div>

      <section
        className="workspace shell"
        aria-label={mode === "verify" ? "Run an audit" : "Discover changes"}
      >
        {mode === "verify" ? (
          <>
            <IntakePanel
              v1={slots.v1}
              v2={slots.v2}
              v1Meta={metas.v1}
              v2Meta={metas.v2}
              notes={notes}
              busy={busy}
              demoBusy={demoBusy}
              error={error}
              onSelect={setFile}
              onMeta={setMeta}
              onNotes={setNotes}
              onRun={runVerify}
              onLoadDemo={loadDemo}
            />
            <StatusPanel busy={busy} report={report} />
          </>
        ) : (
          <>
            <DiscoverIntakePanel
              preFinal={slots.v1}
              final={slots.v2}
              preFinalMeta={metas.v1}
              finalMeta={metas.v2}
              busy={busy}
              error={error}
              onSelect={setFile}
              onMeta={setMeta}
              onRun={runDiscover}
            />
            <DiscoverStatusPanel busy={busy} report={discoverReport} />
          </>
        )}
      </section>

      <div ref={reportRef} className="report__anchor" />
      {mode === "verify" && report ? (
        <ReportSection
          report={report}
          v1Url={slots.v1?.url ?? null}
          v2Url={slots.v2?.url ?? null}
          v1Name={slots.v1?.file.name ?? "—"}
          v2Name={slots.v2?.file.name ?? "—"}
          selectedId={selectedId}
          seek={seek}
          onSelect={select}
          onExport={exportAudit}
          exportState={exportState}
          exportNote={exportNote}
        />
      ) : null}

      {mode === "discover" && discoverReport ? (
        <DiscoverReportSection
          report={discoverReport}
          preFinalUrl={slots.v1?.url ?? null}
          finalUrl={slots.v2?.url ?? null}
          preFinalName={slots.v1?.file.name ?? "—"}
          finalName={slots.v2?.file.name ?? "—"}
          selectedId={discoverSelectedId}
          seek={discoverSeek}
          onSelect={selectDiscover}
          onExport={exportDiscover}
          exportState={exportState}
          exportNote={exportNote}
        />
      ) : null}
    </>
  );
}
