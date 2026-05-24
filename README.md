# Wolf CoG OS - Release 1.0

A governed cognitive operating system built on Debian Trixie, infused with
autonomous runtime behavior.

## Overview

Wolf CoG OS is not a traditional Linux distribution. It is a self-configuring,
self-installing, governed cognitive runtime fused into a Debian-based body.

This system behaves less like a passive operating system and more like an
adaptive runtime organism:

- It installs itself.
- It configures RAID automatically.
- It detects hardware and adapts.
- It installs Windows `.exe` files automatically using Wine.
- It maintains a governed cognitive spine beneath the desktop.
- It behaves with intent, not passivity.

Wolf CoG OS is an experiment in agentic operating system design, blending
traditional Linux with a cognitive runtime that acts with autonomy and
structure.

## Features

### Cognitive Runtime Integration

A governed runtime embedded directly into the OS, providing adaptive behavior
and system-level decision-making.

### Autonomous Installer

On first boot, Wolf CoG OS can:

- detect system topology;
- partition disks;
- configure RAID arrays;
- install itself without user intervention.

### Automatic Windows Compatibility
Windows Executable Support Requires Wine
Wolf Cog OS does not ship with Wine pre‑installed.
If you want .exe files to auto‑launch through the governed UL/Wine bridge, you must install Wine manually.

Without Wine:

.exe files will not run

The auto‑launcher will remain inactive

Right‑click menu options for “Run in Wolf Cog OS” will not appear

To enable Windows app support:  
Install Wine (or Wine‑Staging) from your package manager, then reboot or log out/in so Wolf Cog OS can detect it.
Drop a `.exe` file into the system and Wolf CoG OS can:

- detect it;
- configure Wine;
- install it automatically;
- manage prefixes intelligently.

### Hardware-Aware Behavior

The system adapts to:

- single-drive setups;
- multi-drive RAID;
- SSD/HDD mixes;
- different CPU/GPU environments.

### A New Species Of OS

Wolf CoG OS is not a theme, not a remaster, and not a script bundle. It is a
runtime organism built on top of Debian.

## Download

The intact ISO is hosted on Google Drive:

```text
Wolf-CoG-OS-metal-fixed.iso
https://drive.google.com/file/d/1RwStvSOvMVdCmvLKZOAWmL2wYPrR3pmh/view?usp=sharing
```

SHA-256:

```text
F77638110EB1ECF97202302594AD5E5E19D6A0469F56ED1516A04D7A464CB615  Wolf-CoG-OS-metal-fixed.iso
```

## Release 1.0 Battle Scars

Wolf CoG OS 1.0 was not produced by a clean one-shot build. It came out of a
real bare-metal recovery.

The original install would not boot. The failure was called early as a
bootloader issue, and the forensic pass proved it:

- kernel present;
- initrd present;
- GRUB config valid;
- root UUID correct;
- EFI System Partition present but empty.

The system had a body, but firmware had nothing to launch.

The repair path:

1. Mounted the physical ST350 drive through WSL.
2. Verified the root partition UUID and GRUB menu entries.
3. Rebuilt GRUB into the UEFI fallback boot path.
4. Repaired initramfs/Plymouth failures that caused `Attempted to kill init`.
5. Set a real password for the existing `jon` user.
6. Restored setuid permissions on `sudo`, `su`, and the polkit helper.
7. Stabilized LightDM/Xorg for bare-metal boot.
8. Booted the physical hard drive into a graphical desktop.
9. Remastered the fixed metal install into a new live ISO.
10. Added `live-boot` and `live-config`, rebuilt initrd, rebuilt SquashFS, and
    generated the final hybrid BIOS/UEFI image.

It took three major remaster passes to get to the bootable release:

1. First remaster: captured the repaired filesystem into an ISO.
2. Liveboot remaster: added live-boot/live-config so the ISO could find its
   SquashFS root.
3. Metal-fixed remaster: rebuilt from the successfully booted bare-metal system
   after sudo, polkit, initramfs, LightDM, and GPU fallback repairs.

Final artifact:

```text
C:\wolf\Wolf-CoG-OS-metal-fixed.iso
```

## Status

This is an experimental early release. Use in VMs or non-critical hardware
until you understand its behavior.

Wolf CoG OS is designed for:

- researchers;
- tinkerers;
- OS architects;
- chaos engineers;
- cognitive runtime explorers.

If you are expecting a normal Linux distro, you are in the wrong forest.

## Support The Project

If you enjoy the chaos, the engineering, or the vision behind Wolf CoG OS, you
can support development here:

```text
https://buymeacoffee.com/Chaosgoblinus
```

## License

Open for experimentation. Forks welcome. Chaos encouraged. Governance required.

## Creator

Jon Halstead

AI Systems Architect, Cognitive Runtime Designer, and founder of the Chaos
Goblinus Engineering Tradition.
