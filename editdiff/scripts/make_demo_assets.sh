#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/sample"
mkdir -p "$OUT"
ffmpeg -y \
  -f lavfi -i "testsrc2=size=640x360:rate=30:duration=12" \
  -f lavfi -i "sine=frequency=440:sample_rate=48000:duration=12" \
  -filter_complex "[0:v]split=2[v1][v2b];[v2b]drawbox=x=80:y=95:w=480:h=170:color=white@0.92:t=fill:enable='between(t,5,7)',drawbox=x=0:y=0:w=640:h=360:color=black@0.28:t=fill:enable='between(t,8,10)'[v2];[1:a]asplit=2[a1][a2b];[a2b]volume=volume=0:enable='between(t,1.5,4.5)'[a2]" \
  -map "[v1]" -map "[a1]" -c:v libx264 -preset veryfast -crf 22 -c:a aac -shortest "$OUT/demo-v1.mp4" \
  -map "[v2]" -map "[a2]" -c:v libx264 -preset veryfast -crf 22 -c:a aac -shortest "$OUT/demo-v2.mp4"
echo "Created $OUT/demo-v1.mp4 and demo-v2.mp4"
