"""
raid_proposal.py — Phase A.2 governed RAID proposals (observe + propose + approve only).

No mdadm apply, no formatting, no destructive changes. HAL/storage inventory
feeds candidate groups; GRE gates scan and approve; Pattern Ledger records audits.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from device_storage_manager import DeviceStorageManager
from governance_invariant_engine import (
    ExecutionContext,
    ModuleContract,
    build_execution_context,
    build_gre,
    cogos_root,
)
from pattern_ledger import PatternLedger


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


RAID_PROFILES: Dict[str, Dict[str, Any]] = {
    "speed": {
        "profile": "speed",
        "level": "raid0",
        "label": "Speed (RAID 0)",
        "min_disks": 2,
        "description": "Maximum throughput; no redundancy.",
    },
    "safety": {
        "profile": "safety",
        "level": "raid1",
        "label": "Safety (RAID 1)",
        "min_disks": 2,
        "description": "Mirror pair for redundancy.",
    },
    "balanced": {
        "profile": "balanced",
        "level": "raid10",
        "label": "Balanced (RAID 10)",
        "min_disks": 4,
        "description": "Striped mirrors for speed and safety (4+ disks).",
    },
}

SIZE_TOLERANCE = 0.05
MIN_DISK_BYTES = 32 * 1024 * 1024 * 1024


def _similar_size(a: int, b: int) -> bool:
    if not a or not b:
        return False
    hi = max(a, b)
    return abs(a - b) / hi <= SIZE_TOLERANCE


def _disk_candidates(devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for device in devices:
        path = str(device.get("path", ""))
        if not path.startswith("/dev/"):
            continue
        if device.get("removable"):
            continue
        if device.get("class") == "system":
            continue
        if device.get("partitions"):
            continue
        size = int(device.get("size_bytes") or 0)
        if size < MIN_DISK_BYTES:
            continue
        name = device.get("name", Path(path).name)
        if name.startswith(("loop", "ram", "dm-", "md")):
            continue
        out.append(device)
    return out


def _group_disks(disks: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    unused = list(disks)
    groups: List[List[Dict[str, Any]]] = []
    while unused:
        seed = unused.pop(0)
        group = [seed]
        rest: List[Dict[str, Any]] = []
        seed_size = int(seed.get("size_bytes") or 0)
        for disk in unused:
            if _similar_size(seed_size, int(disk.get("size_bytes") or 0)):
                group.append(disk)
            else:
                rest.append(disk)
        unused = rest
        if len(group) >= 2:
            groups.append(group)
    return groups


def _profiles_for_count(count: int) -> List[str]:
    names: List[str] = []
    if count >= 2:
        names.extend(["speed", "safety"])
    if count >= 4:
        names.append("balanced")
    return names


@dataclass
class RaidProposalService:
    root: Path = cogos_root()

    def __post_init__(self) -> None:
        self.proposal_dir = self.root / "memory" / "storage" / "raid_proposals"
        self.trace_path = self.root / "memory" / "traces" / "raid_proposals.jsonl"
        self.log_path = self.root / "memory" / "logs" / "raid_proposals.json"
        self.proposal_dir.mkdir(parents=True, exist_ok=True)
        self.trace_path.parent.mkdir(parents=True, exist_ok=True)
        self._gre = build_gre()
        self._gre.register_module(
            ModuleContract(
                module_id="RAID",
                lane_id="STORAGE",
                subject="HAL",
                required_input_fields=["action"],
                governance_bindings=["Λ.2", "Λ.3", "Λ.7"],
                allowed_subjects=("HAL", "CoGOS", "operator"),
            )
        )
        self._ledger = PatternLedger()

    def _trace(self, kind: str, detail: Dict[str, Any]) -> None:
        row = {"ts": utc_now(), "kind": kind, **detail}
        with self.trace_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    def _write_snapshot(self, proposals: List[Dict[str, Any]]) -> None:
        payload = {
            "ok": True,
            "timestamp": utc_now(),
            "count": len(proposals),
            "proposals": proposals,
            "profiles": RAID_PROFILES,
            "policy": {
                "destructive_apply": False,
                "size_tolerance": SIZE_TOLERANCE,
                "min_disk_gib": 32,
            },
        }
        self.log_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _governed(
        self,
        action: str,
        payload: Dict[str, Any],
        *,
        mode: str = "automatic",
        execute=None,
    ) -> Tuple[Dict[str, Any], bool]:
        ctx = build_execution_context(
            self._gre,
            "RAID",
            {"action": action, **payload},
            lane_id="STORAGE",
            subject="HAL",
            declared_bindings=["Λ.2", "Λ.3", "Λ.7"],
        )
        result = self._gre.enforce(ctx, execute=execute, mode=mode)
        if result.audit_record:
            self._ledger.ingest_gre_chain([result.audit_record])
        out = {
            "ok": result.passed,
            "action": action,
            "violations": [
                {"id": v.invariant_id, "description": v.description, "severity": v.severity.value}
                for v in result.violations
            ],
        }
        if result.output is not None:
            if isinstance(result.output, dict):
                out.update(result.output)
            else:
                out["result"] = result.output
        return out, result.passed

    def _build_proposals(self, inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
        disks = _disk_candidates(inventory.get("devices", []))
        proposals: List[Dict[str, Any]] = []
        stamp = time.strftime("%Y%m%d-%H%M%S")

        for idx, group in enumerate(_group_disks(disks)):
            paths = [str(d.get("path")) for d in group]
            sizes = [int(d.get("size_bytes") or 0) for d in group]
            for profile_name in _profiles_for_count(len(group)):
                spec = RAID_PROFILES[profile_name]
                proposal_id = f"raid-{stamp}-{idx}-{profile_name}"
                record = {
                    "ok": True,
                    "id": proposal_id,
                    "status": "proposed",
                    "profile": profile_name,
                    "level": spec["level"],
                    "label": spec["label"],
                    "description": spec["description"],
                    "devices": paths,
                    "device_count": len(paths),
                    "size_bytes_min": min(sizes),
                    "size_bytes_max": max(sizes),
                    "destructive": False,
                    "apply_blocked": True,
                    "operator_note": "Proposal only. Use Manual mode to approve; mdadm apply is not enabled in MVP.",
                    "timestamp": utc_now(),
                    "governance": {"module_id": "RAID", "lane_id": "STORAGE"},
                }
                path = self.proposal_dir / f"{proposal_id}.json"
                path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                record["path"] = str(path)
                proposals.append(record)
        return proposals

    def scan(self, *, mode: str = "automatic") -> Dict[str, Any]:
        def _execute(ctx: ExecutionContext) -> Dict[str, Any]:
            inv = DeviceStorageManager(self.root).inventory()
            proposals = self._build_proposals(inv)
            self._write_snapshot(proposals)
            self._trace("scan", {"count": len(proposals)})
            return {"proposals": proposals, "device_count": len(inv.get("devices", []))}

        out, _ = self._governed("scan", {}, mode=mode, execute=_execute)
        return out

    def list_proposals(self, limit: int = 40) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for path in sorted(self.proposal_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            try:
                row = json.loads(path.read_text(encoding="utf-8-sig"))
                row["path"] = str(path)
                rows.append(row)
            except Exception:
                continue
        return rows

    def get_proposal(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        path = self.proposal_dir / f"{proposal_id}.json"
        if not path.exists():
            return None
        row = json.loads(path.read_text(encoding="utf-8-sig"))
        row["path"] = str(path)
        return row

    def approve(self, proposal_id: str, *, profile_id: str = "operator", mode: str = "manual") -> Dict[str, Any]:
        proposal = self.get_proposal(proposal_id)
        if not proposal:
            return {"ok": False, "reason": "proposal not found", "proposal_id": proposal_id}
        if proposal.get("status") == "approved":
            return {"ok": True, "proposal_id": proposal_id, "status": "approved", "note": "already approved"}

        if mode != "manual" and profile_id != "operator":
            return {
                "ok": False,
                "reason": "RAID approve requires manual mode or operator profile",
                "proposal_id": proposal_id,
            }

        def _execute(ctx: ExecutionContext) -> Dict[str, Any]:
            proposal["status"] = "approved"
            proposal["approved_at"] = utc_now()
            proposal["approved_by"] = profile_id
            proposal["apply_blocked"] = True
            path = Path(proposal["path"])
            path.write_text(json.dumps(proposal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            self._trace("approve", {"proposal_id": proposal_id, "profile_id": profile_id})
            self._write_snapshot(self.list_proposals())
            return {"proposal_id": proposal_id, "status": "approved", "apply_blocked": True}

        out, passed = self._governed(
            "approve",
            {"proposal_id": proposal_id, "profile_id": profile_id},
            mode="manual",
            execute=_execute,
        )
        if not passed:
            out["ok"] = False
        return out

    def status(self) -> Dict[str, Any]:
        proposals = self.list_proposals()
        return {
            "ok": True,
            "timestamp": utc_now(),
            "count": len(proposals),
            "proposed": sum(1 for p in proposals if p.get("status") == "proposed"),
            "approved": sum(1 for p in proposals if p.get("status") == "approved"),
            "profiles": RAID_PROFILES,
            "log_path": str(self.log_path),
            "proposals": proposals[:12],
        }


def raid_proposal_status() -> Dict[str, Any]:
    return RaidProposalService().status()
