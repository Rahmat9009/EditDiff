"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { analyze, ApiError, checkHealth, fetchAuditExport } from "./lib/api";
import type { Report } from "./lib/types";
import type { MediaMeta, MediaSlot } from "./components/DropZone";
import { Hero } from "./components/Hero";
import { IntakePanel } from "./components/IntakePanel";
import { ReportSection } from "./components/ReportSection";
import { SiteHeader } from "./components/SiteHeader";
import { StatusPanel } from "./components/StatusPanel";

type Slots = { v1: MediaSlot | null; v2: MediaSlot | null };

export default function Home() {
  const [slots, setSlots] = useState<Slots>({ v1: null, v2: null });
  const [metas, setMetas] = useState<{ v1: MediaMeta | null; v2: MediaMeta | null }>({
    v1: null,
    v2: null,
  });
  const [notes, setNotes] = useState("");
  const [report, setReport] = useState<Report | null>(null);
  const [busy, setBusy] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);
  const [error, setError] = useState("");
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [seek, setSeek] = useState<{ time: number; nonce: number } | null>(null);
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

  useEffect(() => {
    const controller = new AbortController();
    checkHealth(controller.signal).then((online) => {
      if (!controller.signal.aborted) setApiOnline(online);
    });
    return () => controller.abort();
  }, []);

  const setFile = useCallback((role: "v1" | "v2", file: File | null) => {
    setReport(null);
    setSelectedId(null);
    setSeek(null);
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
      setNotes(demoNotes);
      setReport(null);
      setSelectedId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the demo files.");
    } finally {
      setDemoBusy(false);
    }
  }, [setFile]);

  const run = useCallback(async () => {
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
      setApiOnline(true);
      const first = next.results[0];
      if (first) {
        setSelectedId(first.request.id);
        const time = first.evidence.timestamp_seconds ?? first.request.timestamp_seconds ?? null;
        if (time !== null && time !== undefined) {
          nonce.current += 1;
          setSeek({ time, nonce: nonce.current });
        }
      }
      window.requestAnimationFrame(() =>
        reportRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }),
      );
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        if (err.offline) setApiOnline(false);
      } else {
        setError(err instanceof Error ? err.message : "Analysis failed.");
      }
    } finally {
      setBusy(false);
    }
  }, [notes]);

  const exportAudit = useCallback(async () => {
    if (!report) return;
    setExportState("working");
    setExportNote("");
    try {
      const remote = await fetchAuditExport(report);
      const blob =
        remote ??
        new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `editdiff-${report.report_id}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
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

  return (
    <>
      <SiteHeader apiOnline={apiOnline} />
      <main>
        <Hero />

        <section className="workspace shell" aria-label="Run an audit">
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
            onRun={run}
            onLoadDemo={loadDemo}
          />
          <StatusPanel busy={busy} report={report} />
        </section>

        <div ref={reportRef} />
        {report ? (
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
      </main>

      <footer className="site-foot">
        <div className="shell">
          <p>EditDiff · revision QA for creators and editors · evidence before assertion</p>
          <p className="muted">
            Verdicts use audio and visual measurements, with optional semantic inspection.
            Unsupported certainty is marked REVIEW.
          </p>
        </div>
      </footer>
    </>
  );
}
