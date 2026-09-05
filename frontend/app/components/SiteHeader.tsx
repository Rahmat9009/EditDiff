import { API_BASE } from "../lib/api";

type Props = { apiOnline: boolean | null };

export function SiteHeader({ apiOnline }: Props) {
  const label = apiOnline === null ? "Checking API" : apiOnline ? "API online" : "API offline";
  const state = apiOnline === null ? "pending" : apiOnline ? "online" : "offline";
  return (
    <header className="masthead">
      <div className="shell masthead__inner">
        <a className="brand" href="#top">
          {/* Official mark, recoloured to the shipped palette. Fixed box so the
              masthead height never shifts while the image loads. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            className="brand__mark"
            src="/brand/editdiff-mark.png"
            alt=""
            width={40}
            height={40}
            decoding="async"
          />
          <span className="brand__name">EditDiff</span>
          <span className="brand__claim">Prove every revision landed.</span>
        </a>
        <p className={`api-chip api-chip--${state}`} title={API_BASE}>
          <span className="api-chip__dot" aria-hidden="true" />
          {label}
        </p>
      </div>
    </header>
  );
}
