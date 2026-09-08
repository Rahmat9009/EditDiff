"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, fetchReleaseGateExport, runReleaseGate } from "../../lib/api";
import { downloadBlob } from "../../lib/download";
import {
  DECISION_LABEL,
  RELEASE_DECISIONS,
  type ReleaseGateResult,
} from "../../lib/releaseGate";
import { useApiHealthContext } from "../../lib/useApiHealth";
import type { MediaMeta, MediaSlot } from "../DropZone";
import { ReleaseGateIntakePanel } from "./ReleaseGateIntakePanel";
import {
  CHANGE_PREFIX,
  REVISION_PREFIX,
  ReleaseGateReportSection,
  TECHNICAL_PREFIX,
} from "./ReleaseGateReportSection";
import { ReleaseGateStatusPanel } from "./ReleaseGateStatusPanel";

type Role = "baseline" | "candidate";
type Slots = Record<Role, MediaSlot | null>;
type Metas = Record<Role, MediaMeta | null>;

/**
 * Release Gate. One question — is this final export ready to publish — answered
 * against the frozen /release-gate contract. Nothing is synthesised locally:
 * with no gate endpoint on the API, the page says so and shows no result.
 */
export function ReleaseGateWorkspace() {
  const { reportApiState } = useApiHealthContext();

  const [slots, setSlots] = useState<Slots>({ baseline: null, candidate: null });
  const [metas, setMetas] = useState<Metas>({ baseline: null, candidate: null });
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState<ReleaseGateResult | null>(null);

  const [busy, setBusy] = useState(false);
  const [demoBusy, setDemoBusy] = useState(false);
  const [error, setError] = useState("");

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [seek, setSeek] = useState<{
    baselineTime: number;
    candidateTime: number;
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
      const { baseline, candidate } = slotsRef.current;
      if (baseline) URL.revokeObjectURL(baseline.url);
      if (candidate) URL.revokeObjectURL(candidate.url);
    },
    [],
  );

  const reportId = result?.report_id ?? null;
  useEffect(() => {
    if (!reportId) return;
    const frame = window.requestAnimationFrame(() => {
      const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      reportRef.current?.scrollIntoView({ behavior: still ? "auto" : "smooth", block: "start" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [reportId]);

  const setFile = useCallback((role: Role, file: File | null) => {
    setResult(null);
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

  const setMeta = useCallback((role: Role, meta: MediaMeta | null) => {
    setMetas((prev) => ({ ...prev, [role]: meta }));
  }, []);

  /**
   * Seek both players to the moment behind whichever finding was picked.
   * Takes the result explicitly so the first selection after a run can be made
   * before React has committed the new result to state.
   */
  const selectIn = useCallback((source: ReleaseGateResult, id: string) => {
    setSelectedId(id);

    let baselineTime: number | null = null;
    let candidateTime: number | null = null;

    if (id.startsWith(REVISION_PREFIX)) {
      const found = source.requested_revisions.find(
        (r) => r.request.id === id.slice(REVISION_PREFIX.length),
      );
      const t = found?.evidence.timestamp_seconds ?? found?.request.timestamp_seconds ?? null;
      baselineTime = t;
      candidateTime = t;
    } else if (id.startsWith(CHANGE_PREFIX)) {
      const found = source.change_assessments.find((c) => c.id === id.slice(CHANGE_PREFIX.length));
      if (found) {
        const pre = found.evidence.pre_final_timestamp_seconds;
        const fin = found.evidence.final_timestamp_seconds;
        baselineTime = pre ?? fin ?? null;
        candidateTime = fin ?? pre ?? null;
      }
    } else if (id.startsWith(TECHNICAL_PREFIX)) {
      const found = source.technical_checks.find((t) => t.id === id.slice(TECHNICAL_PREFIX.length));
      const t = found?.timestamp_seconds ?? null;
      baselineTime = t;
      candidateTime = t;
    }

    if (baselineTime == null && candidateTime == null) return;
    nonce.current += 1;
    setSeek({
      baselineTime: baselineTime ?? candidateTime ?? 0,
      candidateTime: candidateTime ?? baselineTime ?? 0,
      nonce: nonce.current,
    });
  }, []);

  const select = useCallback(
    (id: string) => {
      if (!result) {
        setSelectedId(id);
        return;
      }
      selectIn(result, id);
    },
    [result, selectIn],
  );

  /**
   * The gate has no fixtures of its own yet, so the demo loads the canonical
   * revision pair as baseline / candidate. The result still comes from the API.
   */
  const loadDemo = useCallback(async () => {
    setDemoBusy(true);
    setError("");
    try {
      const [a, b, noteFile] = await Promise.all([
        fetch("/demo/demo-v1.mp4"),
        fetch("/demo/demo-v2.mp4"),
        fetch("/demo/edit-notes.txt"),
      ]);
      if (!a.ok || !b.ok || !noteFile.ok) {
        throw new Error("Demo assets are missing from this build.");
      }
      const [blobA, blobB, demoNotes] = await Promise.all([a.blob(), b.blob(), noteFile.text()]);
      setFile("baseline", new File([blobA], "demo-v1.mp4", { type: "video/mp4" }));
      setFile("candidate", new File([blobB], "demo-v2.mp4", { type: "video/mp4" }));
      setNotes(demoNotes.replace(/\s+$/, ""));
      setResult(null);
      setSelectedId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the demo files.");
    } finally {
      setDemoBusy(false);
    }
  }, [setFile]);

  const run = useCallback(async () => {
    const { baseline, candidate } = slotsRef.current;
    if (!baseline || !candidate) {
      setError("Add both the baseline and the release candidate.");
      return;
    }
    setBusy(true);
    setError("");
    setResult(null);
    setSelectedId(null);
    setExportNote("");
    try {
      const next = await runReleaseGate(baseline.file, candidate.file, notes);
      setResult(next);
      reportApiState(true);

      const firstRevision = next.requested_revisions[0];
      const firstChange = next.change_assessments[0];
      if (firstRevision) {
        selectIn(next, `${REVISION_PREFIX}${firstRevision.request.id}`);
      } else if (firstChange) {
        selectIn(next, `${CHANGE_PREFIX}${firstChange.id}`);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
        if (err.offline) reportApiState(false);
      } else {
        setError(err instanceof Error ? err.message : "Release gate failed.");
      }
    } finally {
      setBusy(false);
    }
  }, [notes, reportApiState, selectIn]);

  const exportRecord = useCallback(async () => {
    if (!result) return;
    setExportState("working");
    setExportNote("");
    try {
      const remote = await fetchReleaseGateExport(result);
      const blob =
        remote ?? new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
      downloadBlob(blob, `editdiff-release-gate-${result.report_id}.json`);
      setExportState("idle");
      setExportNote(
        remote
          ? "Release record JSON downloaded from the API."
          : "The API export could not be reached or validated. Downloaded the result already in this browser as JSON.",
      );
    } catch {
      setExportState("error");
      setExportNote("Export failed. Print / PDF still works offline.");
    }
  }, [result]);

  return (
    <>
      <header className="page-head page-head--gate">
        <div className="shell page-head__inner">
          <div>
            <p className="eyebrow">Release Gate</p>
            <h1>Is this final export ready to publish?</h1>
            <p className="lede">
              One pass over the release candidate: whether the requested revisions landed, whether
              anything changed that nobody asked for, whether the technical checks hold, and what
              that adds up to.
            </p>
          </div>
          <dl className="legend legend--decisions" aria-label="What each release decision means">
            {RELEASE_DECISIONS.map((d) => (
              <div key={d}>
                <dt>
                  <span
                    className={`decision-chip decision-chip--${d.toLowerCase().replaceAll("_", "-")}`}
                  >
                    {DECISION_LABEL[d]}
                  </span>
                </dt>
                <dd>
                  {d === "READY_TO_PUBLISH"
                    ? "No unresolved changes detected above current thresholds."
                    : d === "NEEDS_REVIEW"
                      ? "Evidence is incomplete or ambiguous. A human decides."
                      : "Evidence contradicts the release. Do not publish yet."}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      </header>

      <section className="workspace shell" aria-label="Run the release gate">
        <ReleaseGateIntakePanel
          baseline={slots.baseline}
          candidate={slots.candidate}
          baselineMeta={metas.baseline}
          candidateMeta={metas.candidate}
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
        <ReleaseGateStatusPanel busy={busy} result={result} />
      </section>

      <div ref={reportRef} className="report__anchor" />
      {result ? (
        <ReleaseGateReportSection
          result={result}
          baselineUrl={slots.baseline?.url ?? null}
          candidateUrl={slots.candidate?.url ?? null}
          baselineName={slots.baseline?.file.name ?? "—"}
          candidateName={slots.candidate?.file.name ?? "—"}
          selectedId={selectedId}
          seek={seek}
          onSelect={select}
          onExport={exportRecord}
          exportState={exportState}
          exportNote={exportNote}
        />
      ) : null}
    </>
  );
}
