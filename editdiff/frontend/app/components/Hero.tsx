import { VERDICT_MEANING } from "../lib/format";
import { VERDICTS } from "../lib/types";
import { VerdictBadge } from "./VerdictBadge";

const STEPS = [
  { n: "01", title: "Paste the revision notes", body: "The exact list you sent your editor, one request per line." },
  { n: "02", title: "Drop both exports", body: "Previous cut and revised cut, checked against your revision notes." },
  { n: "03", title: "Read the evidence ledger", body: "Every request gets a verdict, a timestamp and before/after proof." },
];

export function Hero() {
  return (
    <section className="hero" id="top">
      <div className="shell hero__inner">
        <div className="hero__lead">
          <p className="eyebrow">Revision verification for video teams</p>
          <h1>
            Prove every
            <br />
            <em>revision</em> landed.
          </h1>
          <p className="lede">
            You send an editor revision notes. EditDiff checks the new export against those exact
            notes and returns a timestamped PASS / FAIL / REVIEW ledger — with the frames, audio and
            timing evidence behind each verdict.
          </p>
          <p className="hero__meta">
            Audio &amp; visual signals · Optional semantic checks · Inspectable evidence
          </p>
        </div>
        <div className="hero__signal" aria-hidden="true">
          <span /><span /><span /><span /><span /><span />
        </div>
      </div>

      <div className="shell hero__rails">
        <ol className="steps">
          {STEPS.map((s) => (
            <li key={s.n}>
              <span className="steps__n">{s.n}</span>
              <h2>{s.title}</h2>
              <p>{s.body}</p>
            </li>
          ))}
        </ol>
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
    </section>
  );
}
