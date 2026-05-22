#!/usr/bin/env bash
set -euo pipefail

# Linux/WSL helper for building Wolf CoG OS ISO.
# Run from repo root: bash scripts/linux-remaster-cogos.sh [base.iso]

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BASE_ISO="${1:-$REPO_ROOT/debian-live-13.4.0-amd64-cinnamon.iso}"
TAG="${COGOS_TAG:-12.20.0-wolf-os}"

export COGOS_TAG="$TAG"
exec bash "$REPO_ROOT/scripts/build_trixie_cogos.sh" "$BASE_ISO"
