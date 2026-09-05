import { VERDICT_MEANING } from "../lib/format";
import { VERDICTS } from "../lib/types";
import { VerdictBadge } from "./VerdictBadge";

export function Hero() {
  return (
    <section className="hero" id="top">
      <div className="shell hero__inner">
        <div className="hero__lead">
          <h1>
            Prove every
            <br />
            <em>revision</em> landed.
          </h1>
          <p className="lede">
            Send the revised export with the notes you gave your editor. EditDiff checks the cut
            against those exact notes and returns a timestamped verdict with the evidence behind it.
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
    </section>
  );
}
