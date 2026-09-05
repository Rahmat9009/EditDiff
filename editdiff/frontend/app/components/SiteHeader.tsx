import { API_BASE } from "../lib/api";

type Props = { apiOnline: boolean | null };

export function SiteHeader({ apiOnline }: Props) {
  const label = apiOnline === null ? "Checking API" : apiOnline ? "API online" : "API offline";
  const state = apiOnline === null ? "pending" : apiOnline ? "online" : "offline";
  return (
    <header className="masthead">
      <div className="shell masthead__inner">
        <a className="brand" href="#top">
          <span className="brand__mark" aria-hidden="true">
            ED
          </span>
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
