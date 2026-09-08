import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "EditDiff — Product home",
  description:
    "Compare two exports to understand what changed, or run the Release Gate before publishing.",
};

export default function ProductHome() {
  return (
    <section className="home shell" aria-labelledby="home-heading">
      <h1 id="home-heading" className="home__title">
        What do you want to check?
      </h1>

      <div className="home__choices">
        <Link className="choice" href="/app/compare">
          <span className="choice__index">01</span>
          <h2>Compare Versions</h2>
          <p>
            Verify requested edits or discover everything that changed between two exports.
          </p>
          <span className="choice__modes">Verify Revisions · Discover Changes</span>
          <span className="choice__go" aria-hidden="true">
            →
          </span>
        </Link>

        <Link className="choice choice--gate" href="/app/release-gate">
          <span className="choice__index">02</span>
          <h2>Release Gate</h2>
          <p>Run final regression and technical QA before publishing.</p>
          <span className="choice__modes">
            Requested revisions · Unexpected changes · Technical QA · Release decision
          </span>
          <span className="choice__go" aria-hidden="true">
            →
          </span>
        </Link>
      </div>

      <p className="home__foot muted">
        Both workflows return a timestamped ledger with the frames and measurements behind every
        line. What the evidence cannot establish is recorded as REVIEW.
      </p>
    </section>
  );
}
