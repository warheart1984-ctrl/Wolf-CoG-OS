# Wolf CoG OS 1.0 - Metal Fixed Release

Wolf CoG OS 1.0 is the first metal-fixed public release of the governed
cognitive operating system line. It is built on Debian Trixie and carries the
Wolf CoG runtime identity:

```text
Wolf CoG OS 12.21 - Governed Cognitive Runtime
```

## Download

The intact ISO is hosted on Google Drive:

```text
https://drive.google.com/file/d/1RwStvSOvMVdCmvLKZOAWmL2wYPrR3pmh/view?usp=sharing
```

File:

```text
Wolf-CoG-OS-metal-fixed.iso
```

SHA-256:

```text
F77638110EB1ECF97202302594AD5E5E19D6A0469F56ED1516A04D7A464CB615  Wolf-CoG-OS-metal-fixed.iso
```

## What Changed

- Rebuilt missing EFI/GRUB bootloader handoff.
- Verified root UUID and GRUB kernel/initrd entries.
- Repaired initramfs/Plymouth crash path.
- Restored `sudo`, `su`, and polkit setuid permissions.
- Confirmed the existing `jon` user and restored login access.
- Stabilized LightDM/Xorg for bare-metal graphical boot.
- Added live ISO support through `live-boot` and `live-config`.
- Rebuilt the final SquashFS payload and hybrid BIOS/UEFI ISO.

## Battle Scars

This release was recovered from a non-booting physical installation and
remastered only after the hard drive booted on bare metal.

The path:

1. The system would not boot, and the failure was called early as a bootloader
   issue.
2. WSL was used to mount the ST350 physical drive and inspect the installed OS.
3. Kernel, initrd, root UUID, and GRUB configuration were all valid.
4. The EFI System Partition was present but empty, so firmware had no loader.
5. GRUB was rebuilt into the EFI fallback path.
6. The system reached the kernel, then hit an init panic.
7. Plymouth/initramfs was repaired and regenerated.
8. The system reached tty login.
9. User login, sudo, polkit, LightDM, Xorg, and GPU fallback were repaired.
10. The hard drive booted into a graphical desktop on bare metal.
11. The fixed system was copied, live-boot support was installed, and the ISO
    was remastered.

Three major ISO passes were produced:

- Initial remaster from the repaired filesystem.
- Liveboot remaster with live root support.
- Metal-fixed remaster from the successfully booted bare-metal state.

## Status

Experimental early release. Use in VMs or non-critical hardware until you
understand its behavior.

If you are expecting a normal Linux distro, you are in the wrong forest.
