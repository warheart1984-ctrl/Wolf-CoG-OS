#!/usr/bin/env bash
# Rebuild Wolf CoG OS ISO from a Debian Cinnamon base image.
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BASE_ISO="${1:-$REPO_ROOT/debian-live-13.4.0-amd64-cinnamon.iso}"
TAG="${COGOS_TAG:-12.20.0-wolf-os}"
STAMP="$(date -u +%Y%m%d%H%M%S)"

export COGOS_TAG="$TAG"
export COGOS_WORK="${COGOS_WORK:-/tmp/wolf-cog-os-build-$STAMP}"
export COGOS_OUT="${COGOS_OUT:-$REPO_ROOT/AI OS Debian Build/output/project-infi-cogos-$TAG.iso}"

echo "Wolf CoG OS remaster"
echo "  base: $BASE_ISO"
echo "  tag:  $TAG"
echo "  out:  $COGOS_OUT"
echo "  work: $COGOS_WORK"

cd "$REPO_ROOT/AI OS Debian Build"
exec bash scripts/build_debian_cogos.sh "$BASE_ISO"
