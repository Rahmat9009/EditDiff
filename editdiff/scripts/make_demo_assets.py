"""Reproducible judge fixture: python scripts/make_demo_assets.py."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import tempfile
import wave

import cv2
import numpy as np

FPS, RATE, DURATION = 20, 16000, 14
ROOT = Path(__file__).resolve().parents[1]


def canonical_notes() -> str:
    spec = json.loads((ROOT / "sample/golden-demo.json").read_text(encoding="utf-8"))
    return "\n".join(item["note"] for item in spec["revisions"]) + "\n"


def sync_public(output: Path) -> None:
    """Public assets are generated copies, never an independently authored fixture."""
    public = ROOT / "frontend/public/demo"
    public.mkdir(parents=True, exist_ok=True)
    for name in ("demo-v1.mp4", "demo-v2.mp4", "edit-notes.txt"):
        shutil.copyfile(output / name, public / name)



def frame(t: float, revised: bool) -> np.ndarray:
    img = np.full((360, 640, 3), (26, 23, 20), np.uint8)
    cv2.putText(img, "EDITDIFF / REVISION LAB", (30, 38), cv2.FONT_HERSHEY_SIMPLEX, .65, (180, 190, 200), 1, cv2.LINE_AA)
    cv2.line(img, (30, 56), (610, 56), (90, 90, 90), 1)
    if t < 3:
        heading, sub = "SOUND CHECK", "Background tone / requested mute"
    elif t < 5:
        heading, sub = ("LAUNCH DAY" if revised else "DRAFT CUT"), "A precise title replacement"
    elif t < 7:
        heading, sub = "DETAIL SHOT", "A closer look at the subject"
        radius = 48
        cv2.circle(img, (490, 230), radius, (80, 200, 220), -1)
        cv2.circle(img, (490, 230), radius // 2, (26, 23, 20), 3)
    elif t < 9:
        heading, sub = "FOREST B-ROLL", "The requested city shot is missing"
        for x in range(350, 620, 45):
            cv2.fillConvexPoly(img, np.array([[x, 175], [x-24, 270], [x+24, 270]]), (90, 160, 80))
    else:
        heading, sub = "KEEP IT MOVING", "Local dead air / matched footage"
    cv2.putText(img, heading, (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.15, (80, 240, 220), 2, cv2.LINE_AA)
    cv2.putText(img, sub, (30, 154), cv2.FONT_HERSHEY_SIMPLEX, .48, (190, 195, 200), 1, cv2.LINE_AA)
    if revised and 5 <= t < 7:
        img = cv2.resize(img[30:330, 53:587], (640, 360), interpolation=cv2.INTER_LINEAR)
    # Continuous, distinctive visual anchors; motion freezes during the silent pause.
    motion_t = 10 if 10 <= t < 11.2 else (t - 1.2 if t >= 11.2 else t)
    x = int(motion_t * 180) % 640
    for shift in (-640, 0, 640):
        cv2.rectangle(img, (x + shift, 300), (x + shift + 160, 355), (70, 210, 190), -1)
    cv2.putText(img, "PROVE EVERY REVISION LANDED", (30, 335), cv2.FONT_HERSHEY_SIMPLEX, .5, (245, 245, 245), 1, cv2.LINE_AA)
    return img


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="editdiff-demo-") as temp:
        work = Path(temp)
        for revised in (False, True):
            duration = DURATION - int(revised)
            raw = work / "video.avi"
            writer = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"MJPG"), FPS, (640, 360))
            if not writer.isOpened():
                raise RuntimeError("Video writer unavailable")
            for i in range(duration * FPS):
                t = i / FPS
                source = t + 1 if revised and t >= 10.1 else t
                writer.write(frame(source, revised))
            writer.release()
            t = np.arange(duration * RATE) / RATE
            source = t + np.where(revised & (t >= 10.1), 1., 0.)
            samples = .18 * np.sin(2 * np.pi * 440 * source)
            samples[(source >= 10) & (source < 11.2)] = 0
            if revised:
                samples[source < 3] = 0
            wav = work / "audio.wav"
            with wave.open(str(wav), "wb") as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(RATE)
                stream.writeframes((samples * 32767).astype('<i2').tobytes())
            target = output / ("demo-v2.mp4" if revised else "demo-v1.mp4")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-i", str(wav),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-shortest", str(target)], check=True, timeout=120)
    (output / "edit-notes.txt").write_text(canonical_notes(), encoding="utf-8", newline="\n")
    print(f"Created deterministic fixture in {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "sample")
    parser.add_argument("--sync-only", action="store_true", help="Copy the checked-in canonical fixture to the frontend")
    args = parser.parse_args()
    if not args.sync_only:
        generate(args.output)
    if args.output.resolve() == (ROOT / "sample").resolve():
        sync_public(args.output)
