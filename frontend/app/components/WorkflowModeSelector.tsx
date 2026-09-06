"use client";

export type WorkflowMode = "verify" | "discover";

type Props = {
  mode: WorkflowMode;
  onChange: (next: WorkflowMode) => void;
  disabled?: boolean;
};

export function WorkflowModeSelector({ mode, onChange, disabled }: Props) {
  return (
    <div className="mode-selector" role="radiogroup" aria-label="Workflow mode">
      <span className="mode-selector__prompt">WHAT DO YOU NEED TO CHECK?</span>
      <div className="mode-selector__options">
        <button
          type="button"
          role="radio"
          aria-checked={mode === "verify"}
          className={`mode-btn ${mode === "verify" ? "is-active" : ""}`}
          onClick={() => onChange("verify")}
          disabled={disabled}
        >
          <span className="mode-btn__glyph" aria-hidden="true">✓</span>
          Verify revisions
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={mode === "discover"}
          className={`mode-btn ${mode === "discover" ? "is-active" : ""}`}
          onClick={() => onChange("discover")}
          disabled={disabled}
        >
          <span className="mode-btn__glyph" aria-hidden="true">◈</span>
          Discover changes
        </button>
      </div>
    </div>
  );
}
