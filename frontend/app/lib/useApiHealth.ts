"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { checkHealth } from "./api";

const API_OFFLINE_RETRY_MS = 5_000;
const API_ONLINE_POLL_MS = 45_000;
const API_HEALTH_TIMEOUT_MS = 10_000;

export type ApiHealth = {
  /** null while the first probe is still in flight. */
  apiOnline: boolean | null;
  /** A real request succeeding or failing is fresher news than the poll. */
  reportApiState: (online: boolean) => void;
};

export const ApiHealthContext = createContext<ApiHealth>({
  apiOnline: null,
  reportApiState: () => {},
});

export function useApiHealthContext(): ApiHealth {
  return useContext(ApiHealthContext);
}

/**
 * Polls /health so the masthead can state plainly whether the API is
 * reachable. Retries fast while offline, slowly once online.
 */
export function useApiHealth(): ApiHealth {
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let disposed = false;
    let retryTimer: number | null = null;
    let requestTimer: number | null = null;
    let controller: AbortController | null = null;

    const pollHealth = async () => {
      if (disposed || controller) return;
      controller = new AbortController();
      requestTimer = window.setTimeout(() => controller?.abort(), API_HEALTH_TIMEOUT_MS);
      const online = await checkHealth(controller.signal);
      if (requestTimer !== null) window.clearTimeout(requestTimer);
      requestTimer = null;
      controller = null;
      if (disposed) return;

      setApiOnline(online);
      retryTimer = window.setTimeout(
        pollHealth,
        online ? API_ONLINE_POLL_MS : API_OFFLINE_RETRY_MS,
      );
    };

    void pollHealth();
    return () => {
      disposed = true;
      if (retryTimer !== null) window.clearTimeout(retryTimer);
      if (requestTimer !== null) window.clearTimeout(requestTimer);
      controller?.abort();
    };
  }, []);

  return { apiOnline, reportApiState: setApiOnline };
}
