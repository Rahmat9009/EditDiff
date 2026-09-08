"use client";

import type { ReactNode } from "react";
import { ApiHealthContext, useApiHealth } from "../lib/useApiHealth";
import { SiteFooter } from "./SiteFooter";
import { SiteHeader } from "./SiteHeader";

/** Shared shell for every /app route: masthead with API state, plus footer. */
export function ProductChrome({ children }: { children: ReactNode }) {
  const health = useApiHealth();
  return (
    <ApiHealthContext.Provider value={health}>
      <SiteHeader apiOnline={health.apiOnline} />
      <main className="product">{children}</main>
      <SiteFooter />
    </ApiHealthContext.Provider>
  );
}
