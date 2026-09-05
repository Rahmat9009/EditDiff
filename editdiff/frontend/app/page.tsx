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

const DEMO_NOTES = `00:03 mute the background audio
00:05 tighten the dead air before the title card
00:06 change the on-screen title
00:09 punch in / crop tighter
00:11 replace shot with b-roll`;

const STARTER_NOTES = `00:03 mute the background audio
00:06 change the on-screen title
00:09 punch in / crop tighter`;

type Slots = { v1: MediaSlot | null; v2: MediaSlot | null };

export default function Home() {
  const [slots, setSlots] = useState<Slots>({ v1: null, v2: null });
  const [metas, setMetas] = useState<{ v1: MediaMeta | null; v2: MediaMeta | null }>({
    v1: null,
    v2: null,
  });
  const [notes, setNotes] = useState(STARTER_NOTES);
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
    checkHealth(controller.signal).then(setApiOnline);
    return () => controller.abort();
  }, []);

  const setFile = useCallback((role: "v1" | "v2", file: File | null) => {
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
      const [a, b] = await Promise.all([
        fetch("/demo/demo-v1.mp4"),
        fetch("/demo/demo-v2.mp4"),
      ]);
      if (!a.ok || !b.ok) throw new Error("Demo assets are missing from this build.");
      const [blobA, blobB] = await Promise.all([a.blob(), b.blob()]);
      setFile("v1", new File([blobA], "demo-v1.mp4", { type: "video/mp4" }));
      setFile("v2", new File([blobB], "demo-v2.mp4", { type: "video/mp4" }));
      setNotes(DEMO_NOTES);
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
      link.download = `editdiff-${report.report_id}.${remote ? "bin" : "json"}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setExportState("idle");
      setExportNote(
        remote
          ? "Signed audit export downloaded from the API."
          : "The API has no audit-export endpoint yet, so the full report JSON was downloaded instead. Use Print / PDF for a client-ready version.",
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
            Verdicts come from deterministic audio and visual measurement of your two exports.
            Nothing is asserted that the evidence does not support.
          </p>
        </div>
      </footer>
    </>
  );
}
