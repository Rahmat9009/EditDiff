import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";
import assert from "node:assert/strict";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const sample = resolve(root, "sample");
const publicDemo = resolve(root, "frontend/public/demo");

const spec = JSON.parse(readFileSync(resolve(sample, "golden-demo.json"), "utf8"));
const notes = spec.revisions.map((r) => r.note).join("\n") + "\n";
assert.equal(readFileSync(resolve(sample, "edit-notes.txt"), "utf8").replaceAll("\r\n", "\n"), notes);

/* Both goldens ship the same way: the browser copy must match the canonical
   fixture byte for byte, or the demo is testing something the backend is not. */
const mirrored = [
  "demo-v1.mp4",
  "demo-v2.mp4",
  "edit-notes.txt",
  "release-gate-pre-final.mp4",
  "release-gate-final.mp4",
  "release-gate-notes.txt",
];
for (const file of mirrored) {
  assert.ok(
    readFileSync(resolve(sample, file)).equals(readFileSync(resolve(publicDemo, file))),
    `Stale public demo ${file}. Re-copy it from sample/ (see scripts/make_demo_assets.py and scripts/make_release_gate_assets.py).`,
  );
}

/* The Release Gate golden expects exactly one requested revision. */
const gateGolden = JSON.parse(readFileSync(resolve(sample, "release-gate-golden.json"), "utf8"));
const gateNotes = readFileSync(resolve(sample, "release-gate-notes.txt"), "utf8")
  .replaceAll("\r\n", "\n")
  .split("\n")
  .filter((line) => line.trim().length > 0);
assert.equal(
  gateNotes.length,
  gateGolden.expected_requested_verdicts.length,
  "Release Gate notes and expected verdicts disagree on how many revisions are requested.",
);

console.log(
  "Golden demos: Verify and Release Gate public assets match the canonical fixtures.",
);
