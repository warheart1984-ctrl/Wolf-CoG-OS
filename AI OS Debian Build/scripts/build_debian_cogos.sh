#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/build_debian_cogos.sh [/path/to/debian-live-13.4.0-amd64-cinnamon.iso]

Default ISO path (repo top level):
  ../debian-live-13.4.0-amd64-cinnamon.iso

Output:
  output/project-infi-aris-debian-cinnamon-full-os-v12.iso

Reuses CoGOS payload from:
  ../AI OS Trixie Build/payload

Required Linux tools:
  unsquashfs mksquashfs xorriso rsync find

Notes:
  Set COGOS_XATTRS=1 to preserve SquashFS xattrs. The default is an
  unprivileged WSL-friendly path that uses -no-xattrs because Debian live
  images contain security.capability entries that require root to restore.
  Set COGOS_BOOT_PROFILE=normal to make governed boot the default. The
  default is hp-safe, which bypasses CoGOS PID1 proof and disables splash/
  early modesetting so old hardware can reach Debian first.
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/.." && pwd)"
ISO="${1:-$REPO_ROOT/debian-live-13.4.0-amd64-cinnamon.iso}"
WORK="${COGOS_WORK:-$ROOT/work}"
COGOS_VERSION="${COGOS_TAG:-12.15.0-k32-plane}"
COGOS_VERSION_BASE="${COGOS_VERSION%%-*}"
COGOS_VERSION_SHORT="$(python3 -c "v='${COGOS_VERSION_BASE}'; p=v.split('.'); print('.'.join(p[:2]) if len(p)>=3 else v)")"
COGOS_CODENAME="${COGOS_VERSION#*-}"
COGOS_CODENAME="${COGOS_CODENAME/k32/k}"
COGOS_BUILD_DATE="${COGOS_BUILD_DATE:-$(date -u +%Y-%m-%d)}"
COGOS_OS_MENU="${COGOS_OS_MENU:-Wolf CoG OS ${COGOS_VERSION_SHORT} (Governed Cognitive Runtime)}"
OUT="${COGOS_OUT:-$ROOT/output/project-infi-cogos-${COGOS_VERSION}.iso}"
PAYLOAD="${COGOS_PAYLOAD:-$REPO_ROOT/AI OS Trixie Build/payload}"
LOGO_SRC="$ROOT/branding/wolf_cogos_logo.png"

patch_iso_installer_branding() {
  local grub_dir="$WORK/iso/boot/grub"
  echo "[1c/8] Patch Wolf CoG OS installer GRUB labels"
  for cfg in "$grub_dir/install.cfg" "$grub_dir/install_start.cfg"; do
    [[ -f "$cfg" ]] || continue
    sed -i \
      -e "s/Graphical installer/Wolf CoG OS graphical installer/g" \
      -e "s/Text installer/Wolf CoG OS text installer/g" \
      -e "s/Start installer/Wolf CoG OS installer/g" \
      -e "s/Advanced install options/Wolf CoG OS advanced install/g" \
      -e "s/Utilities/Wolf CoG OS utilities/g" \
      "$cfg"
  done
  if [[ -f "$grub_dir/grub.cfg" ]]; then
    sed -i "s/Advanced install options/Wolf CoG OS installer/g" "$grub_dir/grub.cfg"
    sed -i "s/Utilities\.\.\./Wolf CoG OS utilities/g" "$grub_dir/grub.cfg"
  fi
}

patch_os_identity() {
  local rootfs="$WORK/rootfs"
  local template="$ROOT/branding/os-release.template"
  local motd_template="$ROOT/branding/motd.template"
  echo "[4b/8] Patch Wolf CoG OS identity (${COGOS_VERSION_SHORT} – ${COGOS_CODENAME})"

  if [[ -f "$template" ]]; then
    sed -e "s/@COGOS_VERSION_SHORT@/${COGOS_VERSION_SHORT}/g" \
        -e "s/@COGOS_CODENAME@/${COGOS_CODENAME}/g" \
        -e "s/@COGOS_BUILD_DATE@/${COGOS_BUILD_DATE}/g" \
      "$template" > "$rootfs/etc/os-release"
  else
    cat > "$rootfs/etc/os-release" <<EOF
NAME="Wolf CoG OS"
PRETTY_NAME="Wolf CoG OS ${COGOS_VERSION_SHORT} – Governed Cognitive Runtime"
VERSION="${COGOS_VERSION_SHORT}"
VERSION_ID="${COGOS_VERSION_SHORT}"
VERSION_CODENAME="${COGOS_CODENAME}"
ID=wolfcog
ID_LIKE=debian
VARIANT="Governance Edition"
VARIANT_ID=gov
BUILD_ID="${COGOS_BUILD_DATE}"
EOF
  fi

  if [[ -f "$rootfs/usr/lib/os-release" ]]; then
    cp "$rootfs/etc/os-release" "$rootfs/usr/lib/os-release"
  fi

  printf 'Wolf CoG OS %s – Governed Cognitive Runtime\n \\l\n' "$COGOS_VERSION_SHORT" > "$rootfs/etc/issue"
  printf 'Wolf CoG OS %s – Governed Cognitive Runtime\n' "$COGOS_VERSION_SHORT" > "$rootfs/etc/issue.net"

  if [[ -f "$motd_template" ]]; then
    cp "$motd_template" "$rootfs/etc/motd"
  else
    cat > "$rootfs/etc/motd" <<'EOF'
🐺  Wolf CoG OS – Governed Cognitive Operating System
    Runtime Invariants: Active
    Sigil Enforcement: Enabled
    Provenance Ledger: Online
    Cognitive PID1: Running

Welcome to the substrate.
EOF
  fi

  echo "${COGOS_VERSION_SHORT} (${COGOS_CODENAME})" > "$rootfs/etc/debian_version"
  cat > "$rootfs/etc/lsb-release" <<EOF
DISTRIB_ID=Wolf CoG OS
DISTRIB_RELEASE=${COGOS_VERSION_SHORT}
DISTRIB_CODENAME=${COGOS_CODENAME}
DISTRIB_DESCRIPTION="Wolf CoG OS ${COGOS_VERSION_SHORT} – Governed Cognitive Runtime"
EOF

  if [[ -f "$rootfs/etc/default/grub" ]]; then
    if grep -q '^GRUB_DISTRIBUTOR=' "$rootfs/etc/default/grub"; then
      sed -i 's/^GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR="Wolf CoG OS"/' "$rootfs/etc/default/grub"
    else
      echo 'GRUB_DISTRIBUTOR="Wolf CoG OS"' >> "$rootfs/etc/default/grub"
    fi
  fi

  grep -q 'NAME="Wolf CoG OS"' "$rootfs/etc/os-release"
}

patch_visual_branding() {
  local rootfs="$WORK/rootfs"
  echo "[4c/8] Stage Wolf CoG OS logo and boot splash assets"
  [[ -f "$LOGO_SRC" ]] || {
    echo "Logo not found at $LOGO_SRC (skip visual branding)" >&2
    return 0
  }

  mkdir -p \
    "$rootfs/usr/share/wolfcog/branding" \
    "$rootfs/usr/share/backgrounds/wolfcog" \
    "$rootfs/usr/share/plymouth/themes/wolfcog"

  cp "$LOGO_SRC" "$rootfs/usr/share/wolfcog/branding/logo.png"
  cp "$LOGO_SRC" "$rootfs/usr/share/backgrounds/wolfcog/wolf-cogos.png"
  cp "$LOGO_SRC" "$rootfs/usr/share/plymouth/themes/wolfcog/wolfcog.png"
  if [[ -f "$ROOT/branding/plymouth/wolfcog.plymouth" ]]; then
    cp "$ROOT/branding/plymouth/wolfcog.plymouth" "$rootfs/usr/share/plymouth/themes/wolfcog/wolfcog.plymouth"
  fi

  mkdir -p "$rootfs/etc/plymouth"
  cat > "$rootfs/etc/plymouth/plymouthd.conf" <<EOF
[Daemon]
Theme=wolfcog
ShowDelay=0
DeviceTimeout=8
EOF

  mkdir -p "$rootfs/opt/cogos/branding"
  cp "$LOGO_SRC" "$rootfs/opt/cogos/branding/wolf_cogos_logo.png"
}

for tool in unsquashfs mksquashfs xorriso rsync find grep python3; do
  command -v "$tool" >/dev/null 2>&1 || {
    echo "Missing required tool: $tool" >&2
    exit 2
  }
done

if [[ ! -f "$ISO" ]]; then
  echo "ISO not found: $ISO" >&2
  exit 3
fi

if [[ ! -d "$PAYLOAD" ]]; then
  echo "CoGOS payload not found: $PAYLOAD" >&2
  exit 3
fi

ISO="$(readlink -f "$ISO")"
rm -rf "$WORK"
mkdir -p "$WORK/iso" "$WORK/rootfs" "$ROOT/output"

echo "[1/8] Extract ISO contents"
xorriso -osirrox on -indev "$ISO" -extract / "$WORK/iso" >/dev/null
chmod -R u+w "$WORK/iso"

patch_boot_menu() {
  local grub="$WORK/iso/boot/grub/grub.cfg"
  local config="$WORK/iso/boot/grub/config.cfg"
  local isolinux="$WORK/iso/isolinux"
  local vmlinuz initrd default_entry
  local menu_label="$COGOS_OS_MENU"

  vmlinuz="$(find "$WORK/iso/live" -maxdepth 1 -type f -name 'vmlinuz*' | sort | head -n 1)"
  initrd="$(find "$WORK/iso/live" -maxdepth 1 -type f -name 'initrd*' | sort | head -n 1)"
  if [[ -z "$vmlinuz" || -z "$initrd" || ! -f "$grub" ]]; then
    echo "Boot menu patch skipped; live kernel/initrd/grub.cfg not found." >&2
    return 0
  fi

  vmlinuz="/${vmlinuz#$WORK/iso/}"
  initrd="/${initrd#$WORK/iso/}"
  default_entry=0
  if [[ "${COGOS_BOOT_PROFILE:-hp-safe}" == "normal" ]]; then
    default_entry=1
  fi

  if [[ -f "$config" ]]; then
    python3 - "$config" "$default_entry" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
default_entry = sys.argv[2]
text = path.read_text(encoding="utf-8", errors="replace")
lines = []
for line in text.splitlines():
    if line.startswith("set default="):
        lines.append(f"set default={default_entry}")
    elif line.strip() == "terminal_output gfxterm":
        lines.append("terminal_output console")
    elif line.strip().startswith("set gfxpayload="):
        lines.append("set gfxpayload=text")
    else:
        lines.append(line)
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
  fi

  cat > "$grub" <<EOF
source /boot/grub/config.cfg

# CoGOS hardware-safe live boot.
# Default path for old laptops: get Debian up first, bypass early governance,
# disable splash, and avoid fragile early graphics modesetting.
menuentry "${menu_label} — HP safe boot" --hotkey=h {
	linux	$vmlinuz boot=live components nosplash loglevel=7 systemd.show_status=true plymouth.enable=0 console=tty0 console=ttyS0,115200n8 nomodeset i915.modeset=0 nouveau.modeset=0 radeon.modeset=0 cogos.safe=1 governance=off findiso=\${iso_path}
	initrd	$initrd
}

menuentry "${menu_label}" --hotkey=l {
	linux	$vmlinuz boot=live components loglevel=4 systemd.show_status=true plymouth.enable=1 plymouth.theme=wolfcog console=tty0 console=ttyS0,115200n8 cogos.pid1.strict=0 findiso=\${iso_path}
	initrd	$initrd
}

menuentry "${menu_label} — debug console proof" --hotkey=d {
	linux	$vmlinuz boot=live components nosplash loglevel=7 ignore_loglevel systemd.log_level=debug systemd.log_target=console systemd.journald.forward_to_console=1 plymouth.enable=0 console=tty0 console=ttyS0,115200n8 cogos.pid1.strict=0 findiso=\${iso_path}
	initrd	$initrd
}

menuentry "${menu_label} — recovery shell" --hotkey=r {
	linux	$vmlinuz boot=live components nosplash loglevel=7 systemd.show_status=true plymouth.enable=0 console=tty0 console=ttyS0,115200n8 cogos.recovery=1 findiso=\${iso_path}
	initrd	$initrd
}

menuentry "${menu_label} — fail-safe compatibility" {
	linux	$vmlinuz boot=live components memtest noapic noapm nodma nomce nosmp nosplash nomodeset vga=788 console=tty0 console=ttyS0,115200n8 cogos.safe=1 governance=off
	initrd	$initrd
}

# Installer (if any)
if true; then

source	/boot/grub/install_start.cfg

submenu 'Wolf CoG OS installer ...' --hotkey=a {

	source /boot/grub/theme.cfg

	source	/boot/grub/install.cfg

}
fi

submenu 'Wolf CoG OS utilities ...' --hotkey=u {

	source /boot/grub/theme.cfg

	if [ "\${grub_platform}" = "efi" ]; then
		menuentry "UEFI Firmware Settings" --hotkey=f {
			fwsetup
		}
	fi

	menuentry "Verify integrity of the boot medium" --hotkey=v {
		linux	$vmlinuz boot=live components findiso=\${iso_path} verify-checksums
		initrd	$initrd
	}
}
EOF

  if [[ -d "$isolinux" && -f "$isolinux/live.cfg" ]]; then
    cat > "$isolinux/live.cfg" <<'EOF'
label cogos-hp-safe
	menu label ^Wolf CoG OS - HP safe boot
	menu default
	linux /live/vmlinuz
	initrd /live/initrd.img
	append boot=live components nosplash loglevel=7 systemd.show_status=true plymouth.enable=0 console=tty0 console=ttyS0,115200n8 nomodeset i915.modeset=0 nouveau.modeset=0 radeon.modeset=0 cogos.safe=1 governance=off

label cogos-governed
	menu label Wolf CoG OS - ^governed boot
	linux /live/vmlinuz
	initrd /live/initrd.img
	append boot=live components nosplash loglevel=4 systemd.show_status=true plymouth.enable=0 console=tty0 console=ttyS0,115200n8 cogos.pid1.strict=0

label cogos-debug
	menu label Wolf CoG OS - ^debug console proof
	linux /live/vmlinuz
	initrd /live/initrd.img
	append boot=live components nosplash loglevel=7 ignore_loglevel systemd.log_level=debug systemd.log_target=console systemd.journald.forward_to_console=1 plymouth.enable=0 console=tty0 console=ttyS0,115200n8 cogos.pid1.strict=0

label cogos-recovery
	menu label Wolf CoG OS - ^recovery shell
	linux /live/vmlinuz
	initrd /live/initrd.img
	append boot=live components nosplash loglevel=7 systemd.show_status=true plymouth.enable=0 console=tty0 console=ttyS0,115200n8 cogos.recovery=1

label cogos-failsafe
	menu label Wolf CoG OS - fail-safe compatibility
	linux /live/vmlinuz
	initrd /live/initrd.img
	append boot=live components memtest noapic noapm nodma nomce nosmp nosplash nomodeset vga=788 console=tty0 console=ttyS0,115200n8 cogos.safe=1 governance=off
EOF
  fi

  if [[ -f "$isolinux/isolinux.cfg" ]]; then
    python3 - "$isolinux/isolinux.cfg" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8", errors="replace")
lines = []
for line in text.splitlines():
    if line.startswith("timeout "):
        lines.append("timeout 50")
    else:
        lines.append(line)
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
  fi
}

echo "[1b/8] Patch boot menu for HP-safe defaults"
patch_boot_menu
patch_iso_installer_branding

echo "[2/8] Locate Debian live SquashFS root"
SFS_SOURCE=""
for candidate in \
  "$WORK/iso/live/filesystem.squashfs" \
  "$(find "$WORK/iso/live" -maxdepth 1 -type f -name 'filesystem*.squashfs' 2>/dev/null | head -n 1)" \
  "$(find "$WORK/iso" -maxdepth 3 -type f -name '*.squashfs' 2>/dev/null | sort | head -n 1)"; do
  if [[ -n "$candidate" && -f "$candidate" ]]; then
    SFS_SOURCE="$candidate"
    break
  fi
done
if [[ -z "$SFS_SOURCE" ]]; then
  echo "No SquashFS root file found inside ISO." >&2
  exit 4
fi
SFS_NAME="$(basename "$SFS_SOURCE")"
echo "Using root filesystem image: $SFS_SOURCE"

echo "[3/8] Extract root filesystem: $SFS_NAME"
if [[ "${COGOS_XATTRS:-0}" == "1" ]]; then
  unsquashfs -f -d "$WORK/rootfs" "$SFS_SOURCE"
else
  unsquashfs -no-xattrs -f -d "$WORK/rootfs" "$SFS_SOURCE"
fi

echo "[4/8] Stage Project Infi / ARIS CoGOS payload (Trixie schema)"
rsync -aH \
  --exclude 'opt/cogos/memory/backups/***' \
  --exclude 'opt/cogos/memory/creative/***' \
  --exclude 'opt/cogos/memory/logs/***' \
  --exclude 'opt/cogos/memory/traces/***' \
  --exclude 'opt/cogos/memory/tmp/***' \
  --exclude '**/__pycache__/***' \
  --exclude '*.pyc' \
  "$PAYLOAD/" "$WORK/rootfs/"
mkdir -p \
  "$WORK/rootfs/opt/cogos/memory/backups" \
  "$WORK/rootfs/opt/cogos/memory/creative" \
  "$WORK/rootfs/opt/cogos/memory/logs" \
  "$WORK/rootfs/opt/cogos/memory/traces" \
  "$WORK/rootfs/opt/cogos/memory/tmp"
chmod +x \
  "$WORK/rootfs/opt/cogos/bin/cognitive_init" \
  "$WORK/rootfs/opt/cogos/bin/cogos_shell" \
  "$WORK/rootfs/opt/cogos/bin/cogos_boot.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_daemon.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_dashboard.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_operator_boot.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_nova_repl.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_update.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_hal.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_desktop.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_mesh.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_creative.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_pkg.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_backup.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_eval.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_cockpit.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_ship.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_auto.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_ul_stdlib.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_device_storage.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_first_run.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_manifest.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_recovery.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_hardware_veto.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_install_proof.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_shell_window.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_ul_pkg.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_billing.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_k32.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos_k32_forward.py"

patch_os_identity
patch_visual_branding

echo "[5/8] Install CoGOS operator layer"
mkdir -p "$WORK/rootfs/etc/systemd/system/multi-user.target.wants"
ln -sf ../cogos-guest-proof.service "$WORK/rootfs/etc/systemd/system/multi-user.target.wants/cogos-guest-proof.service"
if [[ -f "$WORK/rootfs/etc/systemd/system/cogos-k32-forward.service" ]]; then
  ln -sf ../cogos-k32-forward.service "$WORK/rootfs/etc/systemd/system/multi-user.target.wants/cogos-k32-forward.service"
fi
if [[ -f "$WORK/rootfs/etc/systemd/system/cogos-wine-bridge.service" ]]; then
  ln -sf ../cogos-wine-bridge.service "$WORK/rootfs/etc/systemd/system/multi-user.target.wants/cogos-wine-bridge.service"
fi
chmod 0644 "$WORK/rootfs/etc/systemd/system/cogos-guest-proof.service"
chmod +x "$WORK/rootfs/etc/init.d/90cogos" \
  "$WORK/rootfs/usr/local/bin/cogos-status" \
  "$WORK/rootfs/usr/local/bin/cogos-shell" \
  "$WORK/rootfs/usr/local/bin/cogos-doctor" \
  "$WORK/rootfs/usr/local/bin/cogos-daemon" \
  "$WORK/rootfs/usr/local/bin/cogos-run" \
  "$WORK/rootfs/usr/local/bin/cogos-task" \
  "$WORK/rootfs/usr/local/bin/cogos-trace" \
  "$WORK/rootfs/usr/local/bin/cogos-law" \
  "$WORK/rootfs/usr/local/bin/cogos-admit" \
  "$WORK/rootfs/usr/local/bin/cogos-snapshot" \
  "$WORK/rootfs/usr/local/bin/cogos-reflect" \
  "$WORK/rootfs/usr/local/bin/cogos-dashboard" \
  "$WORK/rootfs/usr/local/bin/cogos-dashboard-start" \
  "$WORK/rootfs/usr/local/bin/cogos-dashboard-stop" \
  "$WORK/rootfs/usr/local/bin/cogos-desktop-hint" \
  "$WORK/rootfs/usr/local/bin/cogos-verify-trace" \
  "$WORK/rootfs/usr/local/bin/cogos-governance-test" \
  "$WORK/rootfs/usr/local/bin/cogos-module" \
  "$WORK/rootfs/usr/local/bin/cogos-traits" \
  "$WORK/rootfs/usr/local/bin/cogos-patterns" \
  "$WORK/rootfs/usr/local/bin/cogos-proof" \
  "$WORK/rootfs/usr/local/bin/cogos-operator" \
  "$WORK/rootfs/usr/local/bin/cogos-perf" \
  "$WORK/rootfs/usr/local/bin/cogos-pid1-proof" \
  "$WORK/rootfs/usr/local/bin/cogos-ul" \
  "$WORK/rootfs/usr/local/bin/cogos-voss" \
  "$WORK/rootfs/usr/local/bin/cogos-desktop-start" \
  "$WORK/rootfs/usr/local/bin/cogos-hal-start" \
  "$WORK/rootfs/usr/local/bin/cogos-cockpit" \
  "$WORK/rootfs/usr/local/bin/cogos-pkg" \
  "$WORK/rootfs/usr/local/bin/cogos-backup" \
  "$WORK/rootfs/usr/local/bin/cogos-eval" \
  "$WORK/rootfs/usr/local/bin/cogos-ship" \
  "$WORK/rootfs/usr/local/bin/cogos-guest-proof" \
  "$WORK/rootfs/usr/local/bin/cogos-persist" \
  "$WORK/rootfs/usr/local/bin/cogos-install" \
  "$WORK/rootfs/usr/local/bin/cogos-auto" \
  "$WORK/rootfs/usr/local/bin/cogos-ul-stdlib" \
  "$WORK/rootfs/usr/local/bin/cogos-device-storage" \
  "$WORK/rootfs/usr/local/bin/cogos-first-run" \
  "$WORK/rootfs/usr/local/bin/cogos-manifest" \
  "$WORK/rootfs/usr/local/bin/cogos-recovery" \
  "$WORK/rootfs/usr/local/bin/cogos-hardware-veto" \
  "$WORK/rootfs/usr/local/bin/cogos-install-proof" \
  "$WORK/rootfs/usr/local/bin/cogos-shell-start" \
  "$WORK/rootfs/usr/local/bin/cogos-ul-pkg" \
  "$WORK/rootfs/usr/local/bin/cogos-billing" \
  "$WORK/rootfs/usr/local/bin/cogos-k32" \
  "$WORK/rootfs/usr/local/bin/cogos-k32-forward" \
  "$WORK/rootfs/opt/cogos/bin/cogos_ul_bridge.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos-wine-bridge.py" \
  "$WORK/rootfs/opt/cogos/bin/cogos-win-launcher" \
  "$WORK/rootfs/opt/cogos/bin/wolf-wine" \
  "$WORK/rootfs/opt/cogos/bin/build-wine-shim.sh"
ln -sf /opt/cogos/bin/cogos_ul_bridge.py "$WORK/rootfs/usr/local/bin/cogos-ul-bridge"
ln -sf /opt/cogos/bin/cogos-wine-bridge.py "$WORK/rootfs/usr/local/bin/cogos-wine-bridge"
ln -sf /opt/cogos/bin/cogos-win-launcher "$WORK/rootfs/usr/local/bin/cogos-win-launcher"
ln -sf /opt/cogos/bin/wolf-wine "$WORK/rootfs/usr/local/bin/wolf-wine"
if [[ -x "$WORK/rootfs/usr/bin/update-mime-database" ]]; then
  chroot "$WORK/rootfs" update-mime-database /usr/share/mime >/dev/null 2>&1 || true
fi
if [[ -x "$WORK/rootfs/usr/bin/update-desktop-database" ]]; then
  chroot "$WORK/rootfs" update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
echo "[5b/8] Build wine-wolf-bridge preload shim"
COGOS_ROOT="$WORK/rootfs/opt/cogos" bash "$WORK/rootfs/opt/cogos/bin/build-wine-shim.sh" || true
chmod +x \
  "$WORK/rootfs/opt/cogos/modules/local/trace_analyzer/trace_analyzer.py" \
  "$WORK/rootfs/opt/cogos/modules/local/bad_mutator/bad_mutator.py" \
  "$WORK/rootfs/opt/cogos/modules/local/invalid_output/invalid_output.py" \
  "$WORK/rootfs/opt/cogos/modules/local/slow_module/slow_module.py"

echo "[6/8] Install CoGOS PID 1 gatekeeper"
NATIVE_INIT_REAL=""
for candidate in \
  "$WORK/rootfs/usr/sbin/init" \
  "$WORK/rootfs/sbin/init"; do
  if [[ -L "$candidate" || -f "$candidate" ]]; then
    NATIVE_INIT_REAL="$(readlink -f "$candidate" 2>/dev/null || echo "$candidate")"
    break
  fi
done
if [[ -z "$NATIVE_INIT_REAL" || ! -e "$NATIVE_INIT_REAL" ]]; then
  echo "Native init not found at /usr/sbin/init or /sbin/init." >&2
  exit 5
fi
if [[ "$NATIVE_INIT_REAL" == "$WORK/rootfs/opt/cogos/bin/cognitive_init" ]]; then
  echo "Native init already points to CoGOS before preservation." >&2
  exit 5
fi
if [[ ! -e "$WORK/rootfs/usr/sbin/init.original" ]]; then
  cp -a "$NATIVE_INIT_REAL" "$WORK/rootfs/usr/sbin/init.original"
fi
chmod +x "$WORK/rootfs/usr/sbin/init.original"
rm -f "$WORK/rootfs/usr/sbin/init"
ln -s /opt/cogos/bin/cognitive_init "$WORK/rootfs/usr/sbin/init"
if [[ -e "$WORK/rootfs/sbin" ]]; then
  rm -f "$WORK/rootfs/sbin/init"
  ln -s /opt/cogos/bin/cognitive_init "$WORK/rootfs/sbin/init"
fi
[[ "$(readlink "$WORK/rootfs/usr/sbin/init")" == "/opt/cogos/bin/cognitive_init" ]] || {
  echo "/usr/sbin/init does not resolve to CoGOS cognitive_init." >&2
  exit 5
}
echo "Preserved native init: /usr/sbin/init.original from ${NATIVE_INIT_REAL#$WORK/rootfs}"

echo "[7/8] Rebuild SquashFS"
if [[ "${COGOS_XATTRS:-0}" == "1" ]]; then
  mksquashfs "$WORK/rootfs" "$SFS_SOURCE" -comp xz -b 1M -noappend -all-root
else
  mksquashfs "$WORK/rootfs" "$SFS_SOURCE" -comp xz -b 1M -noappend -all-root -no-xattrs
fi

echo "[8/8] Rebuild ISO (replay Debian live boot images from source ISO)"
rm -f "$OUT"
xorriso -indev "$ISO" -outdev "$OUT" \
  -boot_image any replay \
  -map "$WORK/iso" "/" \
  -commit >/dev/null

echo "Built: $OUT"
sha256sum "$OUT" | tee "${OUT}.sha256"
