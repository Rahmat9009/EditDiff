import { metricLabel, metricValue, signedDelta } from "../lib/format";
import type { Metric } from "../lib/types";

export function MetricTable({ metrics }: { metrics: Metric[] }) {
  if (!metrics?.length) return <p className="muted">No deterministic signals were recorded.</p>;
  return (
    <table className="metrics">
      <caption className="visually-hidden">Deterministic signals behind this verdict</caption>
      <thead>
        <tr>
          <th scope="col">Signal</th>
          <th scope="col">V1</th>
          <th scope="col">V2</th>
          <th scope="col">Δ</th>
        </tr>
      </thead>
      <tbody>
        {metrics.map((m) => (
          <tr key={m.name}>
            <th scope="row">
              {metricLabel(m.name)}
              {m.unit ? <span className="metrics__unit">{m.unit}</span> : null}
            </th>
            <td>{metricValue(m.v1, m.unit)}</td>
            <td>{metricValue(m.v2, m.unit)}</td>
            <td>{signedDelta(m.delta)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
