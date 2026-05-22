# Wolf-CoG-OS
Wolf CoG OS — a governed cognitive operating system with invariant runtime, sigil enforcement, and persistent provenance ledger.
🐺 Wolf CoG OS
A governed cognitive operating system with invariant runtime, sigil enforcement, and persistent provenance ledger.
Wolf CoG OS is a first‑generation governed cognitive operating system.
It embeds governance directly into the runtime — not as policy, not as filters, but as structural invariants that shape cognition, planning, and action.

This is not a Linux distro with tweaks.
This is a new substrate.

🧠 Core Principles
1. Governance is a primitive
Wolf CoG OS enforces invariants at the runtime level:

Invariant Engine — non‑bypassable constraints

Sigil Enforcement Layer — identity‑bound permissions

Provenance Ledger — immutable causal history

Cognitive PID1 — governed init for all cognition

2. Cognition is stateful and traceable
Every action, plan, and transformation is:

Proposed

Evaluated

Approved

Logged

3. The system must survive contact with reality
Wolf CoG OS is designed to run on:

Real firmware

Real disks

Real home directories

Real multi‑machine meshes

Not just QEMU.

🚀 Features
Governed Runtime
Invariant engine

Sigil‑aware enforcement

Ledger‑backed provenance

Cognitive PID1

Automatic Mode
Watches real directories

Organizes plans

Suggests actions

Writes to ledger

RAID (Governed)
Proposal + approve path

Trusted apply path (manual for now)

Mesh
Sigil‑based trust

Multi‑peer governance

Local family mesh first

Creative Lanes
Story Forge

Beat Box

Governed pipelines

UL (Unified Language)
stdlib 0.2/0.3

Namespaces

Substrate verbs

🛠️ Build Wolf CoG OS (ISO)
Code
./build_debian_cogos.sh
Outputs:

Code
Wolf-CoG-OS-1.0-Lupus-Prime.iso
Includes:

Wolf branding

os-release

motd/issue

GRUB theme

Plymouth governed boot

Logo assets

💽 Metal Proof (MAKE_IT_REAL.md)
Wolf CoG OS is only “real” when it runs on metal.

Metal Proof Checklist
[ ] USB boot

[ ] Cinnamon visible

[ ] cogos-pid1-proof on hardware

[ ] cogos-eval on hardware

[ ] cogos-install to disk

[ ] Reboot from disk

[ ] cogos-persist status

[ ] Archive proofs

Run the proof script
Code
scripts/real-hardware-proof.sh
Outputs to:

Code
output/proofs/real-hardware-<date>/
🧪 Daily Driver Validation
Use Wolf CoG OS as your primary environment for 7 days.

Daily checks:

Boots clean

Automatic mode fires at least once

No governance drift

No fallback to another OS

Ledger entries consistent

When complete:

Wolf CoG OS is a governed daily substrate on metal.

🧱 Roadmap
v1.0 — Lupus‑Prime
Metal proof

Automatic mode

USB persistence

Daily driver week

RAID proposal path

2–3 machine family mesh

Creative lanes beyond stubs

Native shell (Tauri/egui)

Deferred
Custom kernel

RAID auto‑apply

Public mesh

Full UL GUI toolkit

Installer initrd rebrand

📁 Repository Structure
Code
Wolf-CoG-OS/
├── build/
├── scripts/
│   ├── real-hardware-proof.sh
│   └── remaster/
├── runtime/
│   ├── invariant-engine/
│   ├── sigil/
│   ├── ledger/
│   └── pid1/
├── ul/
├── creative/
├── mesh/
├── docs/
│   ├── vision/
│   │   └── MAKE_IT_REAL.md
│   └── architecture/
└── output/
🐺 Versioning
Wolf CoG OS uses:

Major.Minor.Revision – Codename

Example:

1.0.0 – Lupus‑Prime

1.1.0 – Night‑Forge

1.2.0 – Silver‑Pulse

2.0.0 – Sovereign‑Howl

📜 License
Choose one:

MIT — maximum adoption

Apache 2.0 — ecosystem + patent safety

GPLv3 — governance stays open

🤝 Contributing
Wolf CoG OS is a governed substrate.
All contributions must:

Pass invariant checks

Include ledger‑ready provenance

Follow sigil‑based trust rules

🐺 Wolf CoG OS
A new species of operating system.

md
## 🐺 Support Wolf CoG OS

Wolf CoG OS is built nights, weekends, and chaos‑goblin energy.  
If you want to fuel the next invariant engine, sigil layer, or creative lane:

**Buy Me a Coffee:** https://buymeacoffee.com/Chaosgoblinus

Your support helps keep the governed substrate evolving.

## Wolf CoG OS 12.20 Clean Build

The current launch build is `12.20.0-wolf-os`.

Local launch ISO proof:

```text
AI OS Debian Build/output/project-infi-cogos-12.20.0-wolf-os.iso
SHA256: 51e80bd2eb7f30479cc3fbf744a94d71da679cf943d6ade49a57588006068961
```

This repository does not store the ISO binary. It stores the payload, overlays, runtime, governance layer, and rebuild scripts so the image can be reproduced from a Debian/Trixie Cinnamon live ISO.

### 12.20 launch features

- Cognitive PID1 install-chain repair: `cogos-install` restores `init.original` from systemd and links `init` to `cognitive_init`.
- Boot-time PID1 safety: `cogos_boot.py --boot` avoids the full eval harness during the boot timeout window.
- Governed Windows app UX: double-click a `.exe` and it routes through `cogos-win-launcher` using the `win.default.safe` profile.
- Wine-Wolf Bridge: Windows apps are admitted through UL App Bridge, assigned an OS-side sigil, and logged to provenance.
- UL App Bridge: PE classifier, handshake, policy envelope, hash-chained bridge provenance, and focused smokes.
- MIME integration: `.exe` files are associated with the Wolf CoG OS Windows launcher in the live image and installed system.
- Rebuildable ISO flow: scripts are included for Linux/WSL users to remaster from a base Debian Cinnamon ISO.
- Faster remaster staging: volatile CoGOS memory logs, traces, and backups are excluded from install/remaster payload copies.

### Rebuild the ISO

From Linux or WSL:

```bash
git clone https://github.com/warheart1984-ctrl/Wolf-CoG-OS
cd Wolf-CoG-OS
bash scripts/build_trixie_cogos.sh /path/to/debian-live-*-cinnamon.iso
```

One-shot validation plus remaster:

```bash
bash scripts/one-shot-wolf-os.sh /path/to/debian-live-*-cinnamon.iso
```

Windows helper:

```powershell
.\scripts\one-shot-launch.ps1 -Tag 12.20.0-wolf-os
```

Manual remaster entrypoint:

```bash
cd "AI OS Debian Build"
COGOS_TAG=12.20.0-wolf-os \
COGOS_WORK=/tmp/project-infi-debian-cogos-build \
bash scripts/build_debian_cogos.sh /path/to/debian-live-*-cinnamon.iso
```

### Launch validation

Focused launch smokes:

```bash
python3 "AI OS Trixie Build/payload/opt/cogos/runtime/ul_app_bridge_smoke.py"
python3 "AI OS Trixie Build/payload/opt/cogos/runtime/wine_wolf_bridge_smoke.py"
python3 "AI OS Trixie Build/payload/opt/cogos/runtime/win_launcher_smoke.py"
```

On metal after flashing:

```bash
cogos-install apply --target /dev/sdX --yes --confirm-erase sdX --allow-removable
cogos-win-launcher ~/Downloads/foo.exe
cogos-wine-bridge status
cogos-ul-bridge verify-ledger
```
