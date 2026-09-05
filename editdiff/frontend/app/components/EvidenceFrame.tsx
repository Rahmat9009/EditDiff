"use client";

import { useState } from "react";
import { assetUrl } from "../lib/api";

type Props = { path: string | null | undefined; label: string; alt: string };

/** Evidence still from the API. Missing or unreachable frames degrade quietly. */
export function EvidenceFrame({ path, label, alt }: Props) {
  const [failed, setFailed] = useState(false);
  const src = assetUrl(path);

  return (
    <figure className="frame">
      {src && !failed ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={alt} loading="lazy" decoding="async" onError={() => setFailed(true)} />
      ) : (
        <div className="frame__missing">
          <span>{failed ? "Frame unavailable" : "No frame captured"}</span>
        </div>
      )}
      <figcaption>{label}</figcaption>
    </figure>
  );
}
