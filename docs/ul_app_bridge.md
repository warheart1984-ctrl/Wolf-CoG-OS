# UL App Bridge

**Name:** UL App Bridge  
**Role:** Governed compatibility membrane — foreign apps speak UL before touching FS/net/proc.

## What ships in v0 (before Wine/Darling hooks)

| Layer | Status |
| --- | --- |
| UL verb surface v1.0.0 | `fs.*`, `net.request`, `proc.spawn`, `log.write`, `tool.invoke`, `handshake` |
| OS-injected sigil | `PidSigilRegistry` — caller cannot forge `sigil` in verbs |
| Policy | `config/ul_app_bridge_policy.json` — win/mac/linux foreign profiles |
| Provenance | Hash-chained `memory/ul_app_bridge/provenance.jsonl` |
| Classifier | PE / Mach-O / ELF magic at exec admission |
| Seccomp spec | `foreign_app_ul_bridge` v0 JSON — apply on Linux at exec (BPF install staged) |
| Proof | `ul_app_bridge_smoke.py` — deny `/etc/shadow`, allow `~/Documents` |

**Not in v0:** Wine/Darling syscall hooks, real seccomp BPF on all syscalls, IPC (COM/D-Bus/shm) enforcement.

## Honest claims

- **Governed mode** = seccomp/LSM + UL verbs (target; BPF wiring is `wine-wolf-bridge` bring-up).
- **LD_PRELOAD** = observability only, not a security boundary.
- **IPC v1** = FS/net/proc governed; COM/D-Bus/shm observed or denied (shm denied in seccomp spec).

## CLI

```bash
cogos-ul-bridge version
cogos-ul-bridge classify /path/to/app.exe
cogos-ul-bridge admit /path/to/app.exe --pid 4321
cogos-ul-bridge invoke ul.fs.read --pid 4321 --args '{"path":"/home/jon/Documents/x.txt"}'
cogos-ul-bridge verify-ledger
cogos-ul-bridge summary --sigil sigil-abc123
```

## Child sigil rules

- `inherit` — same sigil and caps as parent.
- `delegated` — `child_caps = parent_caps ∩ requested_caps` (capability subtraction only).

## Launch

Ships with **`wine-wolf-bridge`** in **`12.18.0-launch`** ISO. See `docs/wine_wolf_bridge.md`.
