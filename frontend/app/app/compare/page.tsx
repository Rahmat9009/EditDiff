import type { Metadata } from "next";
import { Suspense } from "react";
import { CompareWorkspace } from "../../components/CompareWorkspace";

export const metadata: Metadata = {
  title: "EditDiff — Compare Versions",
  description:
    "Verify that requested revisions landed, or discover everything that changed between two exports.",
};

export default function ComparePage() {
  return (
    <Suspense fallback={<p className="shell route-loading">Loading Compare Versions…</p>}>
      <CompareWorkspace />
    </Suspense>
  );
}
