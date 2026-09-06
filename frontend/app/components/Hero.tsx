import { VERDICT_MEANING } from "../lib/format";
import { VERDICTS } from "../lib/types";
import { VerdictBadge } from "./VerdictBadge";

export function Hero() {
  return (
    <section className="hero" id="top">
      <div className="shell hero__inner">
        <div className="hero__lead">
          <h1>
            Revision notes say what should have changed.
            <br />
            EditDiff proves <em>what actually changed</em>.
          </h1>
          <p className="lede">
            Verify requested revisions or compare two exports to discover meaningful changes. EditDiff inspects both cuts and returns a timestamped ledger with the evidence behind it.
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
