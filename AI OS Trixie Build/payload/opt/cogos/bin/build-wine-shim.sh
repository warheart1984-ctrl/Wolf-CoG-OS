#!/usr/bin/env bash
# Build libcogos_wine_preload.so for wine-wolf-bridge (Linux only).
set -euo pipefail
ROOT="${COGOS_ROOT:-/opt/cogos}"
SRC="$ROOT/runtime/wine_wolf_bridge/shim/cogos_wine_preload.c"
OUT="$ROOT/lib/libcogos_wine_preload.so"
mkdir -p "$(dirname "$OUT")"
if [[ "$(uname -s)" != "Linux" ]]; then
  echo "wine shim build skipped (not Linux)"
  exit 0
fi
gcc -shared -fPIC -O2 -o "$OUT" "$SRC" -ldl
echo "Built $OUT"
