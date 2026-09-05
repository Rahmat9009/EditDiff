"use client";

import { FormEvent, useMemo, useState } from "react";

type Verdict = "PASS" | "FAIL" | "REVIEW";
type Metric = { name: string; v1?: number | string | null; v2?: number | string | null; delta?: number | null; unit?: string | null };
type Result = {
  request: { id: string; raw_text: string; kind: string; timestamp_seconds?: number | null };
  verdict: Verdict;
  confidence: number;
  evidence: {
    timestamp_seconds?: number | null;
    v1_frame_path?: string | null;
    v2_frame_path?: string | null;
    metrics: Metric[];
    explanation: string;
  };
};
type Report = { report_id: string; summary: Record<Verdict, number>; results: Result[] };

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const starterNotes = `00:03 mute the background audio\n00:06 change the on-screen title\n00:09 punch in / crop tighter`;

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  const m = Math.floor(n / 60);
  const s = Math.floor(n % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

export default function Home() {
  const [v1, setV1] = useState<File | null>(null);
  const [v2, setV2] = useState<File | null>(null);
  const [notes, setNotes] = useState(starterNotes);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const total = useMemo(() => report ? Object.values(report.summary).reduce((a, b) => a + b, 0) : 0, [report]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!v1 || !v2) {
      setError("Choose both V1 and V2 videos.");
      return;
    }
    setLoading(true);
    setError("");
    setReport(null);
    const body = new FormData();
    body.append("v1", v1);
    body.append("v2", v2);
    body.append("notes", notes);
    try {
      const res = await fetch(`${API}/analyze`, { method: "POST", body });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Analysis failed");
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <header className="nav shell">
        <div className="brand"><span className="mark">ED</span><span>EditDiff</span></div>
        <div className="tag">EVIDENCE, NOT ANOTHER CHATBOT</div>
      </header>

      <section className="hero shell">
        <div>
          <p className="eyebrow">REVISION VERIFICATION FOR VIDEO TEAMS</p>
          <h1>Prove every<br/><em>revision</em> landed.</h1>
          <p className="lede">Drop the previous export, revised export, and editor notes. EditDiff checks every requested change and returns timestamped proof.</p>
        </div>
        <div className="signal" aria-hidden="true"><div></div><div></div><div></div><div></div><div></div></div>
      </section>

      <section className="workspace shell">
        <form className="panel input-panel" onSubmit={submit}>
          <div className="panel-head"><span>01</span><h2>Compare exports</h2></div>
          <div className="upload-grid">
            <label className="drop"><span>V1 · PREVIOUS</span><strong>{v1?.name || "Choose video"}</strong><input type="file" accept="video/*" onChange={e => setV1(e.target.files?.[0] || null)} /></label>
            <label className="drop"><span>V2 · REVISED</span><strong>{v2?.name || "Choose video"}</strong><input type="file" accept="video/*" onChange={e => setV2(e.target.files?.[0] || null)} /></label>
          </div>
          <label className="notes"><span>EDIT NOTES · ONE REQUEST PER LINE</span><textarea value={notes} onChange={e => setNotes(e.target.value)} rows={6} /></label>
          <button className="run" disabled={loading}>{loading ? "VERIFYING…" : "RUN REVISION AUDIT →"}</button>
          {error && <p className="error">{error}</p>}
        </form>

        <aside className="panel score-panel">
          <div className="panel-head"><span>02</span><h2>Revision score</h2></div>
          {!report ? (
            <div className="empty"><div className="radar"></div><p>Your evidence report will appear here.</p></div>
          ) : (
            <>
              <div className="score"><strong>{report.summary.PASS}</strong><span>of {total} verified</span></div>
              <div className="counts">
                <div><b>{report.summary.PASS}</b><span>PASS</span></div>
                <div><b>{report.summary.FAIL}</b><span>FAIL</span></div>
                <div><b>{report.summary.REVIEW}</b><span>REVIEW</span></div>
              </div>
              <p className="report-id">REPORT {report.report_id.toUpperCase()}</p>
            </>
          )}
        </aside>
      </section>

      {report && <section className="results shell">
        <div className="section-title"><span>03</span><h2>Evidence ledger</h2><p>Every verdict is tied to a measurable difference.</p></div>
        <div className="ledger">
          {report.results.map((r, i) => <article className="result" key={r.request.id}>
            <div className="result-top">
              <div className={`pill ${r.verdict.toLowerCase()}`}>{r.verdict}</div>
              <div className="request"><span>{String(i + 1).padStart(2, "0")} · {fmt(r.evidence.timestamp_seconds)}</span><h3>{r.request.raw_text}</h3></div>
              <div className="confidence">{Math.round(r.confidence * 100)}%<span>confidence</span></div>
            </div>
            <div className="proof">
              <div className="frames">
                {r.evidence.v1_frame_path && <figure><img src={`${API}${r.evidence.v1_frame_path}`} alt="V1 evidence frame"/><figcaption>V1 · BEFORE</figcaption></figure>}
                {r.evidence.v2_frame_path && <figure><img src={`${API}${r.evidence.v2_frame_path}`} alt="V2 evidence frame"/><figcaption>V2 · AFTER</figcaption></figure>}
              </div>
              <div className="why"><p>{r.evidence.explanation}</p><dl>{r.evidence.metrics.slice(0,4).map(m => <div key={m.name}><dt>{m.name.replaceAll("_", " ")}</dt><dd>{typeof m.v2 === "number" ? m.v2.toFixed(3) : (m.v2 ?? "—")}</dd></div>)}</dl></div>
            </div>
          </article>)}
        </div>
      </section>}

      <footer className="shell">EditDiff · creator revision QA · evidence-first</footer>
    </main>
  );
}
