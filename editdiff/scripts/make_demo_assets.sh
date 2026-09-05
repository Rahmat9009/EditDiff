#!/usr/bin/env bash
set -euo pipefail
python "$(dirname "$0")/make_demo_assets.py" "$@"
