"""Smoke checks for governed RAID proposals (Phase A.2)."""

from __future__ import annotations

import json
from pathlib import Path

from governance_invariant_engine import cogos_root
from raid_proposal import RaidProposalService, _group_disks, _similar_size


def main() -> int:
    root = cogos_root()
    svc = RaidProposalService(root)

    assert _similar_size(1000, 1020)
    assert not _similar_size(1000, 2000)

    fake_disks = [
        {"path": "/dev/sda", "name": "sda", "size_bytes": 500 * 1024**3, "removable": False, "partitions": []},
        {"path": "/dev/sdb", "name": "sdb", "size_bytes": 510 * 1024**3, "removable": False, "partitions": []},
        {"path": "/dev/sdc", "name": "sdc", "size_bytes": 512 * 1024**3, "removable": False, "partitions": []},
        {"path": "/dev/sdd", "name": "sdd", "size_bytes": 508 * 1024**3, "removable": False, "partitions": []},
    ]
    groups = _group_disks(fake_disks)
    assert len(groups) == 1 and len(groups[0]) == 4

    scan = svc.scan(mode="automatic")
    assert scan.get("ok"), scan

    built = svc._build_proposals({"devices": fake_disks})
    assert len(built) >= 3, built
    for row in built:
        assert row.get("apply_blocked") is True
        assert row.get("destructive") is False

    pid = built[0]["id"]
    approved = svc.approve(pid, profile_id="operator", mode="manual")
    assert approved.get("ok"), approved
    assert approved.get("status") == "approved"
    row = svc.get_proposal(pid)
    assert row and row.get("status") == "approved"

    fresh_id = built[1]["id"]
    denied = svc.approve(fresh_id, profile_id="kid", mode="automatic")
    assert not denied.get("ok"), denied

    status = svc.status()
    assert status.get("ok")
    log_path = root / "memory" / "logs" / "raid_proposals.json"
    assert log_path.exists()
    ledger = root / "memory" / "patterns" / "gre_audit.jsonl"
    if ledger.exists():
        lines = ledger.read_text(encoding="utf-8").strip().splitlines()
        assert any("RAID" in line for line in lines[-20:])

    print("raid_proposal_smoke: ALL PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
