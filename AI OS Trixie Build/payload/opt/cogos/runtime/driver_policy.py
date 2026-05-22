"""Driver policy table: PCI/USB class → module → governed load log."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from governance_invariant_engine import cogos_root


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class DriverPolicyEngine:
    root: Path = cogos_root()

    @property
    def policy_path(self) -> Path:
        return self.root / "config" / "driver_policy.json"

    @property
    def log_path(self) -> Path:
        return self.root / "memory" / "traces" / "driver_loads.jsonl"

    @property
    def approvals_path(self) -> Path:
        return self.root / "memory" / "driver_policy" / "approvals.json"

    def _load_policy(self) -> Dict[str, Any]:
        default = {"version": "1.0", "rules": []}
        if not self.policy_path.exists():
            return default
        try:
            return json.loads(self.policy_path.read_text(encoding="utf-8-sig"))
        except Exception:
            return default

    def _match_rule(self, device: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        match = rule.get("match", {})
        for key, expected in match.items():
            if str(device.get(key, "")).lower() != str(expected).lower():
                return False
        return True

    def classify_device(self, device: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for rule in self._load_policy().get("rules", []):
            if self._match_rule(device, rule):
                return rule
        return None

    def _observe_devices(self) -> List[Dict[str, Any]]:
        observed: List[Dict[str, Any]] = []
        # Linux sysfs PCI/USB hints
        pci = Path("/sys/bus/pci/devices")
        if pci.is_dir():
            for entry in sorted(pci.iterdir())[:32]:
                cls = ""
                vendor = ""
                try:
                    cls = (entry / "class").read_text().strip()[:6] if (entry / "class").exists() else ""
                    vendor = (entry / "vendor").read_text().strip() if (entry / "vendor").exists() else ""
                except OSError:
                    pass
                observed.append({
                    "id": entry.name,
                    "bus": "pci",
                    "class": "unknown" if not cls else "pci",
                    "pci_class": cls,
                    "vendor": vendor,
                    "kind": "pci",
                })
        # Network from HAL-style path
        net = Path("/sys/class/net")
        if net.is_dir():
            for iface in sorted(net.iterdir()):
                if not iface.is_dir() or iface.name == "lo":
                    continue
                kind = "wireless" if (iface / "wireless").exists() else "ethernet"
                observed.append({
                    "id": iface.name,
                    "bus": "kernel",
                    "class": "network",
                    "kind": kind,
                })
        # Fallback: map block devices from storage manager
        try:
            from device_storage_manager import DeviceStorageManager

            inv = DeviceStorageManager().inventory()
            for dev in inv.get("devices", [])[:24]:
                transport = str(dev.get("transport", "block")).lower()
                dev_class = "nvme" if "nvme" in transport else "storage"
                if dev.get("removable"):
                    observed.append({
                        "id": dev.get("name", dev.get("path", "?")),
                        "bus": "usb" if "usb" in transport else "block",
                        "class": "storage",
                        "kind": transport,
                        "size_bytes": dev.get("size_bytes"),
                    })
                else:
                    observed.append({
                        "id": dev.get("name", dev.get("path", "?")),
                        "bus": "block",
                        "class": dev_class,
                        "kind": transport,
                        "size_bytes": dev.get("size_bytes"),
                    })
        except Exception:
            pass
        if not observed:
            observed.append({
                "id": "host-observe",
                "bus": "virtual",
                "class": "unknown",
                "kind": "dev-host",
                "note": "no sysfs on this host; policy table still active",
            })
        return observed

    def _load_approvals(self) -> Dict[str, Any]:
        if not self.approvals_path.exists():
            return {"approved": []}
        try:
            return json.loads(self.approvals_path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {"approved": []}

    def _save_approval(self, device_id: str, rule_id: str) -> None:
        self.approvals_path.parent.mkdir(parents=True, exist_ok=True)
        data = self._load_approvals()
        approved = list(data.get("approved", []))
        row = {"device_id": device_id, "rule_id": rule_id, "ts": _now()}
        if row not in approved:
            approved.append(row)
        data["approved"] = approved[-200:]
        self.approvals_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _is_approved(self, device_id: str, rule_id: str) -> bool:
        for row in self._load_approvals().get("approved", []):
            if row.get("device_id") == device_id and row.get("rule_id") == rule_id:
                return True
        return False

    def _log_decision(self, row: Dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    def evaluate_load(
        self,
        device: Dict[str, Any],
        *,
        profile_id: str = "operator",
        mode: str = "automatic",
        intent_k_layer: Optional[int] = None,
    ) -> Dict[str, Any]:
        rule = self.classify_device(device)
        if not rule:
            decision = {
                "ok": False,
                "allowed": False,
                "device_id": device.get("id"),
                "reason": "no matching policy rule",
                "requires_manual": True,
            }
            self._log_decision({**decision, "ts": _now(), "profile_id": profile_id, "mode": mode, "intent_k_layer": intent_k_layer})
            return decision

        rule_id = rule.get("id", "")
        requires_manual = bool(rule.get("requires_manual"))
        approved = self._is_approved(str(device.get("id", "")), rule_id)
        allowed = not requires_manual or approved or mode == "manual"
        k_threshold = rule.get("k_threshold")
        k_ceiling = rule.get("k_ceiling")
        k_blocked = False
        k_requires_operator = False
        if intent_k_layer is not None:
            if k_ceiling is not None and intent_k_layer > int(k_ceiling):
                allowed = False
                k_blocked = True
            if k_threshold is not None and intent_k_layer >= int(k_threshold):
                k_requires_operator = True
                if profile_id != "operator" and mode != "manual" and not approved:
                    allowed = False
        if profile_id == "kid":
            allowed = False

        decision = {
            "ok": True,
            "allowed": allowed,
            "device_id": device.get("id"),
            "rule_id": rule_id,
            "module": rule.get("module"),
            "requires_manual": requires_manual or k_requires_operator,
            "approved": approved,
            "tier": rule.get("tier"),
            "notes": rule.get("notes", ""),
            "intent_k_layer": intent_k_layer,
            "k_threshold": k_threshold,
            "k_ceiling": k_ceiling,
            "k_blocked": k_blocked,
            "k_requires_operator": k_requires_operator,
        }
        self._log_decision({**decision, "ts": _now(), "profile_id": profile_id, "mode": mode})
        return decision

    def scan(self, *, profile_id: str = "operator") -> Dict[str, Any]:
        devices = self._observe_devices()
        evaluations = [self.evaluate_load(d, profile_id=profile_id) for d in devices]
        pending = sum(1 for e in evaluations if e.get("requires_manual") and not e.get("allowed"))
        return {
            "ok": True,
            "timestamp": _now(),
            "devices": devices,
            "evaluations": evaluations,
            "rules_count": len(self._load_policy().get("rules", [])),
            "pending_manual": pending,
        }

    def approve(self, device_id: str, rule_id: str, *, profile_id: str = "operator") -> Dict[str, Any]:
        if profile_id != "operator":
            return {"ok": False, "reason": "operator profile required"}
        self._save_approval(device_id, rule_id)
        self._log_decision({
            "ts": _now(),
            "kind": "approve",
            "device_id": device_id,
            "rule_id": rule_id,
            "profile_id": profile_id,
        })
        return {"ok": True, "device_id": device_id, "rule_id": rule_id}

    def status(self) -> Dict[str, Any]:
        recent: List[Dict[str, Any]] = []
        if self.log_path.exists():
            try:
                lines = self.log_path.read_text(encoding="utf-8").splitlines()
                for line in lines[-20:]:
                    try:
                        recent.append(json.loads(line))
                    except Exception:
                        continue
            except Exception:
                pass
        scan = self.scan()
        return {
            "ok": True,
            "policy_version": self._load_policy().get("version"),
            "rules_count": len(self._load_policy().get("rules", [])),
            "pending_manual": scan.get("pending_manual", 0),
            "recent_decisions": recent,
            "devices": scan.get("devices", [])[:12],
            "evaluations": scan.get("evaluations", [])[:12],
        }
