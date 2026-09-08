import type { Metadata } from "next";
import { ReleaseGateWorkspace } from "../../components/release-gate/ReleaseGateWorkspace";

export const metadata: Metadata = {
  title: "EditDiff — Release Gate",
  description:
    "Run final regression and technical QA on a release candidate: requested revisions, unexpected changes, technical checks, and one release decision.",
};

export default function ReleaseGatePage() {
  return <ReleaseGateWorkspace />;
}
