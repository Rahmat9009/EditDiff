import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Do not emit AGENTS.md / CLAUDE.md into the frontend package on `next dev`.
  agentRules: false,
};
export default nextConfig;
