#!/usr/bin/env bash
set -u

WORK="${1:-/tmp/cogos-build-launch}"
OUT="${2:-/mnt/e/project-infi/AI OS Debian Build/output/project-infi-cogos-12.18.0-launch.iso}"

ps -eo pid,ppid,stat,etime,cmd | grep -E "$(basename "$WORK")|build_debian_cogos|rsync|unsquashfs|mksquashfs|xorriso|gcc|sha256sum" | grep -v grep || true
echo '---io---'
for p in 80 81 82; do
  if [ -d "/proc/$p" ]; then
    echo "---PID $p---"
    cat "/proc/$p/io" 2>/dev/null || true
    grep -E 'State|VmRSS' "/proc/$p/status" 2>/dev/null || true
  fi
done
echo '---sizes---'
du -sh "$WORK/rootfs" "$WORK/iso" 2>/dev/null || true
echo '---output---'
ls -lh "$OUT" 2>/dev/null || true
echo '---recent---'
find "$WORK/rootfs/opt/cogos" -type f -printf '%T@ %s %p\n' 2>/dev/null | sort -nr | head -10 || true
