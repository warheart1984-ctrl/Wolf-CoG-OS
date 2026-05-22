#!/usr/bin/env bash
# Wolf CoG OS — one-shot smokes + optional ISO remaster (Linux/WSL).
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PAYLOAD="$REPO_ROOT/AI OS Trixie Build/payload/opt/cogos"
TAG="${COGOS_TAG:-12.20.0-wolf-os}"
BASE_ISO="${1:-$REPO_ROOT/debian-live-13.4.0-amd64-cinnamon.iso}"
SKIP_REMASTER="${SKIP_REMASTER:-0}"
SKIP_EVAL="${SKIP_EVAL:-0}"

export COGOS_ROOT="$PAYLOAD"
PY="${COGOS_PYTHON:-python3}"

echo "== Wolf CoG OS one-shot ($TAG) =="
"$PY" "$PAYLOAD/runtime/mesh_physical_smoke.py"
"$PY" "$PAYLOAD/runtime/ul_app_bridge_smoke.py"
"$PY" "$PAYLOAD/runtime/wine_wolf_bridge_smoke.py"
"$PY" "$PAYLOAD/runtime/win_launcher_smoke.py"

if [ "$SKIP_EVAL" != "1" ]; then
  "$PY" "$PAYLOAD/bin/cogos_manifest.py" sign "$PAYLOAD/config/release_manifest.json"
  "$PY" "$PAYLOAD/bin/cogos_ship.py" preflight
  "$PY" "$PAYLOAD/bin/cogos_eval.py" run
fi

if [ "$SKIP_REMASTER" != "1" ]; then
  export COGOS_TAG="$TAG"
  bash "$REPO_ROOT/scripts/build_trixie_cogos.sh" "$BASE_ISO"
fi

echo "Wolf CoG OS one-shot: complete"
