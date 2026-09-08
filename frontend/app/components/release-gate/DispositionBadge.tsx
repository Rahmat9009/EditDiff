import {
  DISPOSITION_GLYPH,
  DISPOSITION_LABEL,
  TECHNICAL_STATUS_GLYPH,
  TECHNICAL_STATUS_LABEL,
  type ChangeDisposition,
  type TechnicalCheckSeverity,
  type TechnicalCheckStatus,
} from "../../lib/releaseGate";

export function DispositionBadge({
  disposition,
  size = "md",
}: {
  disposition: ChangeDisposition;
  size?: "sm" | "md";
}) {
  const tone = disposition.toLowerCase().replaceAll("_", "-");
  return (
    <span className={`disposition disposition--${tone} disposition--${size}`}>
      <span className="disposition__glyph" aria-hidden="true">
        {DISPOSITION_GLYPH[disposition]}
      </span>
      {DISPOSITION_LABEL[disposition]}
    </span>
  );
}

export function TechnicalStatusBadge({
  status,
  size = "md",
}: {
  status: TechnicalCheckStatus;
  size?: "sm" | "md";
}) {
  const tone = status.toLowerCase().replaceAll("_", "-");
  return (
    <span className={`tech-status tech-status--${tone} tech-status--${size}`}>
      <span className="tech-status__glyph" aria-hidden="true">
        {TECHNICAL_STATUS_GLYPH[status]}
      </span>
      {TECHNICAL_STATUS_LABEL[status]}
    </span>
  );
}

export function SeverityTag({ severity }: { severity: TechnicalCheckSeverity }) {
  return (
    <span className={`severity severity--${severity.toLowerCase()}`}>
      {severity === "BLOCKING" ? "Blocking" : "Advisory"}
    </span>
  );
}
