"""Reproducible Release Gate fixture: python scripts/make_release_gate_assets.py."""
from pathlib import Path
import subprocess
import tempfile
import wave

import cv2
import numpy as np


FPS, RATE, DURATION = 20, 16000, 8
ROOT = Path(__file__).resolve().parents[1]


def frame(timestamp: float, final: bool) -> np.ndarray:
    image = np.full((360, 640, 3), (30, 26, 22), np.uint8)
    cv2.putText(image, "EDITDIFF RELEASE GATE", (28, 42), cv2.FONT_HERSHEY_SIMPLEX,
                .8, (230, 235, 240), 2, cv2.LINE_AA)
    cv2.putText(image, "Regression testing for video production", (28, 76),
                cv2.FONT_HERSHEY_SIMPLEX, .52, (150, 190, 205), 1, cv2.LINE_AA)
    x = int(timestamp * 95) % 700 - 60
    cv2.rectangle(image, (x, 145), (x + 150, 270), (50, 170, 210), -1)
    cv2.circle(image, (530, 250), 44, (170, 90, 210), -1)
    cv2.putText(image, f"TIMECODE {timestamp:04.1f}", (28, 330), cv2.FONT_HERSHEY_SIMPLEX,
                .55, (220, 220, 220), 1, cv2.LINE_AA)
    # The baseline carries a persistent approval logo in this region. Its absence
    # in the final is the unrelated accidental regression the gate must surface.
    if 5.0 <= timestamp < 7.0 and not final:
        cv2.rectangle(image, (430, 92), (610, 142), (245, 245, 245), -1)
        cv2.putText(image, "APPROVED", (447, 126), cv2.FONT_HERSHEY_SIMPLEX,
                    .7, (15, 15, 15), 2, cv2.LINE_AA)
    return image


def generate(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="editdiff-release-gate-") as temp:
        work = Path(temp)
        for final in (False, True):
            raw = work / ("final.avi" if final else "pre-final.avi")
            writer = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"MJPG"), FPS, (640, 360))
            if not writer.isOpened():
                raise RuntimeError("Video writer unavailable")
            for index in range(DURATION * FPS):
                writer.write(frame(index / FPS, final))
            writer.release()

            time = np.arange(DURATION * RATE) / RATE
            samples = .18 * np.sin(2 * np.pi * 440 * time)
            if final:
                samples[(time >= .5) & (time < 2.5)] = 0
            wav = work / ("final.wav" if final else "pre-final.wav")
            with wave.open(str(wav), "wb") as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(RATE)
                stream.writeframes((samples * 32767).astype("<i2").tobytes())

            target = output / ("release-gate-final.mp4" if final else "release-gate-pre-final.mp4")
            subprocess.run([
                "ffmpeg", "-v", "error", "-y", "-i", str(raw), "-i", str(wav),
                "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-shortest", str(target),
            ], check=True, timeout=120)
    print(f"Created deterministic Release Gate fixture in {output}")


if __name__ == "__main__":
    generate(ROOT / "sample")
