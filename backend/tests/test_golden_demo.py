import json
from collections import Counter


def test_golden_demo_assets_and_notes(sample):
    spec = json.loads((sample / "golden-demo.json").read_text())
    assert dict(Counter(r["expected_verdict"] for r in spec["revisions"])) == spec["expected_summary"]
    notes = "\n".join(r["note"] for r in spec["revisions"]) + "\n"
    assert (sample / "edit-notes.txt").read_text() == notes
    public = sample.parent / "frontend/public/demo"
    for name in ("demo-v1.mp4", "demo-v2.mp4", "edit-notes.txt"):
        assert (public / name).read_bytes() == (sample / name).read_bytes(), f"Stale public demo: {name}"
