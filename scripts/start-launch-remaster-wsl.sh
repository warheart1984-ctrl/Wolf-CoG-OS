#!/usr/bin/env bash
set -euo pipefail

ROOT="/mnt/e/project-infi"
TAG="${COGOS_TAG:-${1:-12.18.0-launch}}"
WORK="${COGOS_WORK:-${2:-/tmp/cogos-build-launch}}"
OUT_DIR="$ROOT/AI OS Debian Build/output"
SAFE_TAG="${TAG//[^A-Za-z0-9._-]/-}"
LOG="$OUT_DIR/remaster-$SAFE_TAG.log"
ERR="$OUT_DIR/remaster-$SAFE_TAG.err.log"

mkdir -p "$OUT_DIR"

export COGOS_TAG="$TAG"
export COGOS_ROOT="$ROOT/AI OS Trixie Build/payload/opt/cogos"
export COGOS_OUT="$OUT_DIR/project-infi-cogos-$TAG.iso"
export COGOS_WORK="$WORK"

setsid bash "$ROOT/AI OS Debian Build/scripts/build_debian_cogos.sh" \
  "$ROOT/debian-live-13.4.0-amd64-cinnamon.iso" \
  >"$LOG" 2>"$ERR" < /dev/null &

echo "LAUNCH_BUILD_PID=$!"
echo "LOG=$LOG"
echo "ERR=$ERR"
