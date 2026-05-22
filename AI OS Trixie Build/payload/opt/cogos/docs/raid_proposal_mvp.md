# RAID Proposal MVP (Phase A.2)

Governed **proposal-only** RAID. No mdadm apply, no formatting, no silent disk changes.

## Profiles (Automatic mode language)

| Profile | Level | Min disks | Intent |
| --- | --- | --- | --- |
| speed | RAID 0 | 2 | Throughput |
| safety | RAID 1 | 2 | Mirror redundancy |
| balanced | RAID 10 | 4 | Striped mirrors |

Similar whole disks (within 5% size, non-removable, ≥32 GiB, no partitions) are grouped; each group gets applicable profiles.

## Commands

```sh
cogos-device-storage raid-scan
cogos-device-storage raid-list
cogos-device-storage raid-status
cogos-device-storage raid-approve PROPOSAL_ID --profile operator
```

## GRE + ledger

- `raid-scan` and `raid-approve` run through module `RAID` / lane `STORAGE`.
- Audit records append to the Pattern Ledger (`memory/patterns/gre_audit.jsonl`).
- Approve requires **manual mode** or **operator** profile.

## Outputs

- Proposals: `memory/storage/raid_proposals/*.json`
- Snapshot: `memory/logs/raid_proposals.json`
- Trace: `memory/traces/raid_proposals.jsonl`

## Control Center

Device + Storage panel: **Scan RAID proposals**, table with **Approve** (records approval only; `apply_blocked` stays true).

## Next (not in MVP)

- Operator-confirmed mdadm apply behind a separate elevated tier
- SMART health integration
- Hot spare and scrub scheduling
