import type { Metadata } from "next";
import Link from "next/link";
import { SiteFooter } from "./components/SiteFooter";
import { SiteHeader } from "./components/SiteHeader";

export const metadata: Metadata = {
  title: "EditDiff — Regression testing for video production",
  description:
    "Catch missed revisions and accidental changes before they ship. EditDiff verifies requested revisions, detects accidental changes, and runs final release QA between video exports.",
};

export default function LandingPage() {
  return (
    <>
      <SiteHeader />
      <main className="landing" id="top">
        <LandingHero />
        <LandingProblem />
        <LandingWorkflows />
        <LandingEvidence />
        <LandingClose />
      </main>
      <SiteFooter />
    </>
  );
}

/* ------------------------------------------------------------------- hero */

function LandingHero() {
  return (
    <section className="lander-hero">
      <div className="shell lander-hero__inner">
        <p className="eyebrow">Regression testing for video production</p>
        <h1>
          Don&rsquo;t publish a<br />
          <em>broken edit</em>.
        </h1>
        <p className="lede lander-hero__lede">
          EditDiff verifies requested revisions, detects accidental changes, and runs final
          release QA between video exports.
        </p>
        <div className="cta-row">
          <Link className="btn btn--run" href="/app/release-gate">
            Run Release Gate
            <span aria-hidden="true">→</span>
          </Link>
          <Link className="btn btn--secondary btn--lg" href="/app/compare">
            Compare Versions
          </Link>
        </div>
        <p className="lander-hero__promise">
          Catch missed revisions and accidental changes before they ship.
        </p>
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- problem */

function LandingProblem() {
  return (
    <section className="band band--problem" aria-labelledby="problem-heading">
      <div className="shell band__grid">
        <div className="band__lead">
          <p className="eyebrow">The problem</p>
          <h2 id="problem-heading">
            Every export gets checked by a human scrubbing a timeline.
          </h2>
          <p className="band__body">
            An editor sends back version four. Someone opens both files, scrubs to each note,
            and tries to remember what the previous cut looked like. The requested fixes usually
            get checked. The things nobody asked to change usually do not.
          </p>
        </div>
        <ul className="failure-list">
          <li>
            <span className="failure-list__index">01</span>
            <p>A requested fix was marked done but never made it into the export.</p>
          </li>
          <li>
            <span className="failure-list__index">02</span>
            <p>A frame, a caption, or an audio bed changed while something else was fixed.</p>
          </li>
          <li>
            <span className="failure-list__index">03</span>
            <p>The version that ships is not the version that was approved.</p>
          </li>
        </ul>
      </div>
    </section>
  );
}

/* -------------------------------------------------------------- workflows */

function LandingWorkflows() {
  return (
    <>
      <section className="band band--idea" aria-labelledby="idea-heading">
        <div className="shell">
          <h2 id="idea-heading" className="idea">
            Software has regression tests.
            <br />
            Video production doesn&rsquo;t.
            <br />
            <em>EditDiff brings regression testing to video.</em>
          </h2>
        </div>
      </section>

      <section className="band" aria-labelledby="workflows-heading">
        <div className="shell">
          <p className="eyebrow">Two workflows</p>
          <h2 id="workflows-heading" className="band__title">
            One tells you what changed. One tells you whether to publish.
          </h2>

          <div className="workflow-grid">
            <article className="workflow">
              <header className="workflow__head">
                <span className="workflow__index">01</span>
                <h3>Compare Versions</h3>
              </header>
              <p className="workflow__claim">Understand exactly what changed.</p>
              <dl className="workflow__modes">
                <div>
                  <dt>Verify Revisions</dt>
                  <dd>Did the requested edits actually happen?</dd>
                </div>
                <div>
                  <dt>Discover Changes</dt>
                  <dd>What else changed between exports?</dd>
                </div>
              </dl>
              <Link className="workflow__link" href="/app/compare">
                Compare two exports <span aria-hidden="true">→</span>
              </Link>
            </article>

            <article className="workflow workflow--flagship">
              <header className="workflow__head">
                <span className="workflow__index">02</span>
                <h3>Release Gate</h3>
                <span className="workflow__tag">Flagship</span>
              </header>
              <p className="workflow__claim">Run final QA before publishing.</p>
              <ul className="workflow__checks">
                <li>Requested revisions</li>
                <li>Unexpected regressions</li>
                <li>Technical QA</li>
                <li>Release decision</li>
              </ul>
              <p className="workflow__answer">
                Answers one question: <b>is this final export ready to publish?</b>
              </p>
              <Link className="workflow__link" href="/app/release-gate">
                Gate a release candidate <span aria-hidden="true">→</span>
              </Link>
            </article>
          </div>
        </div>
      </section>
    </>
  );
}

/* --------------------------------------------------------------- evidence */

function LandingEvidence() {
  return (
    <section className="band band--evidence" aria-labelledby="evidence-heading">
      <div className="shell band__grid">
        <div className="band__lead">
          <p className="eyebrow">Architecture</p>
          <h2 id="evidence-heading">Evidence first, conclusion second.</h2>
          <p className="band__body">
            EditDiff measures both exports before it says anything about them: aligned timelines,
            bounded search windows, frame and audio signals, thresholds recorded alongside the
            result. Every verdict carries the timestamp, the frames, and the measurements it came
            from.
          </p>
          <p className="pull-quote">AI interprets evidence. It does not invent the evidence.</p>
        </div>

        <ol className="pipeline">
          <li>
            <span className="pipeline__step">Measure</span>
            <p>Both exports are aligned and sampled. Signals are recorded with their thresholds.</p>
          </li>
          <li>
            <span className="pipeline__step">Attribute</span>
            <p>Each finding is bound to a timestamp, a window, and the frames behind it.</p>
          </li>
          <li>
            <span className="pipeline__step">Interpret</span>
            <p>
              Requested intent is checked against what was measured. Disagreement is reported, not
              resolved by guessing.
            </p>
          </li>
          <li>
            <span className="pipeline__step">Report</span>
            <p>
              What cannot be established stays <b>REVIEW</b>. EditDiff does not record a pass the
              evidence does not support.
            </p>
          </li>
        </ol>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ close */

function LandingClose() {
  return (
    <section className="band band--close">
      <div className="shell lander-close">
        <h2>Check the export before it becomes the version everyone saw.</h2>
        <div className="cta-row">
          <Link className="btn btn--run" href="/app/release-gate">
            Run Release Gate
            <span aria-hidden="true">→</span>
          </Link>
          <Link className="btn btn--secondary btn--lg" href="/app/compare">
            Compare Versions
          </Link>
        </div>
      </div>
    </section>
  );
}
