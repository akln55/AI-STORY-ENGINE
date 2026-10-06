#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 tools/check_android_env.py
rm -rf .buildozer bin
buildozer -v android debug
python3 tools/verify_android_staging.py --build-dir .buildozer --source-dir .
