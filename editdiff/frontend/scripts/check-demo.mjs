import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve, dirname } from "node:path";
import assert from "node:assert/strict";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const sample = resolve(root, "sample");
const spec = JSON.parse(readFileSync(resolve(sample, "golden-demo.json"), "utf8"));
const notes = spec.revisions.map((r) => r.note).join("\n") + "\n";
assert.equal(readFileSync(resolve(sample, "edit-notes.txt"), "utf8").replaceAll("\r\n", "\n"), notes);
for (const file of ["demo-v1.mp4", "demo-v2.mp4", "edit-notes.txt"]) {
  assert.ok(readFileSync(resolve(sample, file)).equals(readFileSync(resolve(root, "frontend/public/demo", file))),
    `Stale public demo ${file}. Run python scripts/make_demo_assets.py --sync-only from editdiff/.`);
}
console.log("Golden demo: public videos and notes match the canonical fixture.");
